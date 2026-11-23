#!/usr/bin/env python3
"""Record how cdk diff treats an omitted parameter.

aws-cdk 2.1148.1 defaults to a change set. This stands in for
CloudFormation and STS on localhost and reads the CreateChangeSet
request. An omitted parameter is absent. UsePreviousValue is absent.
A passed parameter is sent as ParameterValue. A parameter with no
default fails `--method=change-set`. The default auto method falls
back to a template diff in that case. `--method=template` rejects
`--parameters`.

The account 123456789012 is the AWS documentation example.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parent
ACCOUNT = "123456789012"
REGION = "us-east-1"

DESCRIBE = """<?xml version="1.0"?>
<DescribeStacksResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
  <DescribeStacksResult><Stacks><member>
    <StackName>ParamStack</StackName>
    <StackId>arn:aws:cloudformation:us-east-1:123456789012:stack/ParamStack/abc</StackId>
    <StackStatus>UPDATE_COMPLETE</StackStatus>
    <Parameters><member>
      <ParameterKey>Name</ParameterKey>
      <ParameterValue>live-value</ParameterValue>
    </member></Parameters>
  </member></Stacks></DescribeStacksResult>
  <ResponseMetadata><RequestId>req</RequestId></ResponseMetadata>
</DescribeStacksResponse>
"""

GET_TEMPLATE = """<?xml version="1.0"?>
<GetTemplateResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
  <GetTemplateResult><TemplateBody>{"Parameters":{"Name":{"Type":"String","Default":"from-default"}}}</TemplateBody></GetTemplateResult>
  <ResponseMetadata><RequestId>req</RequestId></ResponseMetadata>
</GetTemplateResponse>
"""

CHANGESET = """<?xml version="1.0"?>
<CreateChangeSetResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
  <CreateChangeSetResult>
    <Id>arn:aws:cloudformation:us-east-1:123456789012:changeSet/cdk-diff/1</Id>
    <StackId>arn:aws:cloudformation:us-east-1:123456789012:stack/ParamStack/abc</StackId>
  </CreateChangeSetResult>
  <ResponseMetadata><RequestId>req</RequestId></ResponseMetadata>
</CreateChangeSetResponse>
"""

DESCRIBE_CS = """<?xml version="1.0"?>
<DescribeChangeSetResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
  <DescribeChangeSetResult>
    <ChangeSetName>cdk-diff</ChangeSetName>
    <ChangeSetId>arn:aws:cloudformation:us-east-1:123456789012:changeSet/cdk-diff/1</ChangeSetId>
    <StackId>arn:aws:cloudformation:us-east-1:123456789012:stack/ParamStack/abc</StackId>
    <StackName>ParamStack</StackName>
    <Status>CREATE_COMPLETE</Status>
    <ExecutionStatus>AVAILABLE</ExecutionStatus>
    <Changes></Changes>
  </DescribeChangeSetResult>
  <ResponseMetadata><RequestId>req</RequestId></ResponseMetadata>
</DescribeChangeSetResponse>
"""

DELETE_CS = """<?xml version="1.0"?>
<DeleteChangeSetResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
  <ResponseMetadata><RequestId>req</RequestId></ResponseMetadata>
</DeleteChangeSetResponse>
"""

IDENTITY = """<?xml version="1.0"?>
<GetCallerIdentityResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
  <GetCallerIdentityResult>
    <Arn>arn:aws:iam::123456789012:user/fixture</Arn>
    <UserId>fixture-user</UserId>
    <Account>123456789012</Account>
  </GetCallerIdentityResult>
  <ResponseMetadata><RequestId>req</RequestId></ResponseMetadata>
</GetCallerIdentityResponse>
"""


class Handler(BaseHTTPRequestHandler):
    log_path: Path

    def _body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length)

    def _xml(self, body: str, status: int = 200) -> None:
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/xml")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:  # noqa: N802
        raw = self._body()
        target = self.headers.get("X-Amz-Target", "")
        content_type = self.headers.get("Content-Type", "")
        text = raw.decode("utf-8", "replace")
        if "json" in content_type or text.startswith("{"):
            try:
                params = json.loads(text)
            except json.JSONDecodeError:
                params = {}
            action = target
        else:
            parsed = parse_qs(text)
            action = (parsed.get("Action") or [""])[0]
            params = {
                key: values if len(values) > 1 else values[0]
                for key, values in parsed.items()
            }
        name = action or target
        if "GetParameter" in name:
            body = json.dumps(
                {"Parameter": {"Name": params.get("Name", ""), "Type": "String", "Value": "21"}}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/x-amz-json-1.1")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if "GetCallerIdentity" in name:
            self._xml(IDENTITY)
            return
        if "DescribeStacks" in name:
            self._xml(DESCRIBE)
            return
        if "GetTemplate" in name:
            self._xml(GET_TEMPLATE)
            return
        if "CreateChangeSet" in name:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(params) + "\n")
            self._xml(CHANGESET)
            return
        if "DescribeChangeSet" in name:
            self._xml(DESCRIBE_CS)
            return
        if "DeleteChangeSet" in name:
            self._xml(DELETE_CS)
            return
        self._xml("<ErrorResponse><Error><Code>Unknown</Code></Error></ErrorResponse>", 400)

    def log_message(self, fmt: str, *args: object) -> None:
        return


def _serve(log_path: Path) -> tuple[ThreadingHTTPServer, int]:
    Handler.log_path = log_path
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, server.server_address[1]


def _changesets(log_path: Path) -> list[dict[str, object]]:
    if not log_path.is_file() or not log_path.read_text(encoding="utf-8").strip():
        return []
    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _members(params: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in params.items() if str(key).startswith("Parameters.member")}


def _diff(port: int, app: str, extra: list[str], output: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "AWS_ACCESS_KEY_ID": "testing",
            "AWS_SECRET_ACCESS_KEY": "testing",
            "AWS_DEFAULT_REGION": REGION,
            "AWS_ENDPOINT_URL": f"http://127.0.0.1:{port}",
            "AWS_EC2_METADATA_DISABLED": "true",
            "CDK_DEFAULT_ACCOUNT": ACCOUNT,
            "CDK_DEFAULT_REGION": REGION,
        }
    )
    cdk = ROOT / "node_modules" / ".bin" / "cdk"
    return subprocess.run(
        [
            str(cdk),
            "diff",
            "--no-color",
            "--output",
            output,
            "--app",
            f"node {app}",
            *extra,
            "ParamStack",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=90,
    )


def _show(label: str, completed: subprocess.CompletedProcess[str]) -> None:
    print(f"{label} exited {completed.returncode}", file=sys.stderr)
    tail = (completed.stdout + completed.stderr)[-2000:]
    print(tail, file=sys.stderr)


def main() -> int:
    cdk = ROOT / "node_modules" / ".bin" / "cdk"
    if not cdk.is_file():
        subprocess.run(["npm", "ci"], cwd=ROOT, check=True)
    log_path = ROOT / "changesets.jsonl"
    server, port = _serve(log_path)
    output = tempfile.mkdtemp(prefix="cdk-omit-")
    try:
        log_path.write_text("", encoding="utf-8")
        omitted = _diff(port, "app/app.js", [], output)
        omitted_sets = _changesets(log_path)
        if omitted.returncode != 0 or len(omitted_sets) != 1 or _members(omitted_sets[0]):
            _show("omitted", omitted)
            print("an omitted parameter was sent or the default diff did not create one change set", file=sys.stderr)
            return 1
        if any("UsePreviousValue" in key for key in omitted_sets[0]):
            print("the omitted diff sent UsePreviousValue", file=sys.stderr)
            return 1

        log_path.write_text("", encoding="utf-8")
        passed = _diff(
            port, "app/app.js", ["--parameters", "ParamStack:Name=passed-value"], output
        )
        passed_sets = _changesets(log_path)
        members = _members(passed_sets[0]) if passed_sets else {}
        if (
            passed.returncode != 0
            or members.get("Parameters.member.1.ParameterKey") != "Name"
            or members.get("Parameters.member.1.ParameterValue") != "passed-value"
        ):
            _show("passed", passed)
            print("a passed parameter was not sent as ParameterValue", file=sys.stderr)
            return 1

        log_path.write_text("", encoding="utf-8")
        # auto swallows the missing-parameter error and falls back to a
        # template diff. change-set is the path that fails the diff.
        required = _diff(
            port,
            "app/required.js",
            ["--method=change-set", "--parameters", "ParamStack:Name=only-name"],
            output,
        )
        if required.returncode == 0 or "missing a value" not in (required.stdout + required.stderr):
            _show("required", required)
            print("an omitted parameter with no default did not fail the diff", file=sys.stderr)
            return 1
        if _changesets(log_path):
            print("the required-parameter failure still created a change set", file=sys.stderr)
            return 1

        log_path.write_text("", encoding="utf-8")
        template = _diff(
            port,
            "app/app.js",
            ["--method=template", "--parameters", "ParamStack:Name=passed-value"],
            output,
        )
        combined = template.stdout + template.stderr
        if template.returncode == 0 or "cannot be used" not in combined or _changesets(log_path):
            _show("template", template)
            print("template diff accepted parameters or created a change set", file=sys.stderr)
            return 1
    finally:
        server.shutdown()
        log_path.unlink(missing_ok=True)
        shutil.rmtree(output, ignore_errors=True)
    print("cdk diff omits a parameter instead of sending UsePreviousValue")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

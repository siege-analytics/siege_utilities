#!/usr/bin/env python3
"""Require review of credential-bearing URL construction across the package.

This conservative AST guard flags construction even without proving a path to a
log or exception: a request library can include its URL in an exception. It finds
literal/f-string query fields, urlencode(dict) fields and HTTP params=, following
assignments, updates and aliases within a file. Unresolved params= require review.
It is not an interprocedural taint analyzer.
Each exemption identifies one expression in one function and explains its sinks.
Run: python scripts/check_credential_urls.py [package-directory]
"""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote_plus


# Independent of the runtime redactor so removing a protected name cannot weaken
# the guard as well as the diagnostics.
SENSITIVE = frozenset({
    "key", "password", "access_token", "token", "apikey", "api_key",
    "client_secret", "secret", "sig", "x-amz-signature", "auth",
    "signature", "x-goog-signature", "x-amz-security-token",
})
QUERY_FIELD = re.compile(r"[?&#]([^=&#\s]+)=")
HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "head", "options", "request", "Request"})
UNRESOLVED_PARAMS = "<unresolved params>"

# (package-relative path, qualified function, canonical AST expression): reason.
ALLOWLIST = {
    ("geo/census/api.py", "CensusAPI._build_url", "f'&key={self.api_key}'"):
        "Census query authentication: _make_request_with_retry redacts diagnostics "
        "and raises fresh exceptions outside handlers; census sentinel tests enforce it.",
    ("geo/providers/tamu_batch.py", "TAMUBatchGeocoder._tamu_request",
     "urllib.parse.urlencode(params)"):
        "TAMU v4.01 documents query authentication. _tamu_request raises a fresh "
        "redacted error outside handlers and _geocode_single redacts its warning; "
        "TAMU sentinel tests enforce both sinks.",
    ("geo/providers/redistricting_data_hub.py", "RDHClient._fetch_datasets",
     "self._session.get(self.base_url, params=params, timeout=60)"):
        "RDH requires username/password query authentication from _auth_params, "
        "copied into params before adding filters. Listing diagnostics are redacted "
        "and raise a fresh ConnectionError outside the handler; sentinel tests cover it.",
    ("geo/providers/redistricting_data_hub.py", "RDHClient.download_dataset",
     "self._session.get(url, params=self._auth_params(url), timeout=300, stream=True)"):
        "RDH requires query authentication on its host and subdomains. _auth_params "
        "excludes unrelated hosts; download diagnostics are redacted and raise fresh exceptions "
        "without credential-bearing request/response/context; sentinel tests cover it.",
    ("analytics/instagram.py", "InstagramConnector._request_url",
     "self._session.request(method, url, params=req_params, timeout=self._timeout)"):
        "Instagram strips access_token from params and paging URLs and authenticates "
        "with a header. Fresh redacted exceptions and logs are covered by sentinel tests.",
    ("analytics/vista_social.py", "VistaSocialConnector._request",
     "self._session.request(method, url, params=dict(params) if params else None, "
     "json=dict(json_body) if json_body is not None else None, timeout=self._timeout)"):
        "Vista Social installs its bearer token in Authorization. Reviewed callers "
        "supply analytics/date/pagination filters; this forwarding site adds no query "
        "credentials. Caller-supplied secret params are not sanitized by this wrapper.",
    ("analytics/x_twitter.py", "XTwitterConnector._request",
     "self._session.request(method, url, params=req_params, timeout=self._timeout)"):
        "X authenticates with an Authorization header. Reviewed callers supply field, "
        "date and pagination filters; this forwarding site adds no query credentials. "
        "Caller-supplied secret params are not sanitized by this wrapper.",
    ("connectors/dynamics.py", "DynamicsConnector._query_all_odata",
     "self.request('GET', path, params=params)"):
        "Forwards OData select/filter/pagination fields to the header-authenticated "
        "request wrapper; this site does not insert credentials.",
    ("connectors/dynamics.py", "DynamicsConnector.request",
     "self._session.request(method, url, params=dict(params) if params else None, "
     "json=json_body, timeout=self._timeout, **{'headers': dict(headers)} if headers is not None else {})"):
        "Dynamics installs OAuth credentials in Authorization; reviewed callers use "
        "OData query fields. Per-request headers add FetchXML paging annotations "
        "without adding query credentials. Caller-supplied secret params are not sanitized here.",
    ("connectors/hubspot.py", "HubSpotConnector._list_objects",
     "self.request('GET', path, params=params)"):
        "Forwards limit/properties/after pagination fields to the header-authenticated "
        "request wrapper; this site does not insert credentials.",
    ("connectors/hubspot.py", "HubSpotConnector.request",
     "self._session.request(method, url, params=dict(params) if params else None, "
     "json=json_body, timeout=self._timeout)"):
        "HubSpot installs OAuth credentials in Authorization; reviewed callers use "
        "object and pagination fields. Caller-supplied secret params are not sanitized here.",
    ("connectors/salesforce.py", "SalesforceConnector.request",
     "self._session.request(method, url, params=dict(params) if params else None, "
     "json=json_body, timeout=self._timeout)"):
        "Salesforce installs OAuth credentials in Authorization; reviewed callers use "
        "SOQL and object filters. Caller-supplied secret params are not sanitized here.",
    ("connectors/zoho.py", "ZohoConnector._list_records",
     "self.request('GET', path, params=params)"):
        "Forwards page/per_page fields to the header-authenticated request wrapper; "
        "this site does not insert credentials.",
    ("connectors/zoho.py", "ZohoConnector.request",
     "self._session.request(method, url, params=dict(params) if params else None, "
     "json=json_body, timeout=self._timeout)"):
        "Zoho installs OAuth credentials in Authorization; reviewed callers use module "
        "and pagination fields. Caller-supplied secret params are not sanitized here.",
    ("geo/isochrones.py", "_dispatch_request",
     "httpx.post(request_def['url'], headers=request_def['headers'], "
     "params=request_def['params'], json=request_def['json'], timeout=timeout_seconds)"):
        "build_isochrone_request puts the ORS API key in Authorization; query params "
        "are provider options. Custom secret extra_params are not sanitized here.",
    ("geo/isochrones.py", "_dispatch_request",
     "httpx.get(request_def['url'], headers=request_def['headers'], "
     "params={**request_def['params'], **request_def['json']}, timeout=timeout_seconds)"):
        "GET dispatch forwards provider options and routing geometry; supported "
        "builders use header auth or no auth. Custom secret options are not sanitized here.",
    ("geo/providers/nlrb_clients.py", "NLRBDatagovClient.fetch_cases",
     "self._get_session().get(self._base_url, params=params, timeout=self._timeout)"):
        "The public NLRB XML endpoint uses no credentials; params are caller filters. "
        "Caller-supplied secret filters are not sanitized in result.errors.",
}


@dataclass(frozen=True)
class Site:
    path: str
    line: int
    function: str
    expression: str
    parameters: tuple[str, ...]

    @property
    def identity(self) -> tuple[str, str, str]:
        return self.path, self.function, self.expression

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.function}: {', '.join(self.parameters)} in {self.expression}"


def credential_url_sites(source: str, path: str) -> list[Site]:
    """Find sensitive query construction, ignoring comments and docstrings."""
    tree = ast.parse(source, filename=path)
    bindings: dict[str, list[ast.AST]] = {}
    docstrings = set()
    encoders = {"urlencode"}
    request_functions = set(HTTP_METHODS)
    requests_modules = {"requests"}
    positional_gets = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            requests_modules.update(alias.asname or alias.name for alias in node.names
                                    if alias.name == "requests")
        if isinstance(node, ast.ImportFrom) and node.module == "urllib.parse":
            encoders.update(alias.asname or alias.name for alias in node.names if alias.name == "urlencode")
        if isinstance(node, ast.ImportFrom) and node.module in {"requests", "requests.api"}:
            request_functions.update(alias.asname or alias.name for alias in node.names if alias.name in HTTP_METHODS)
            positional_gets.update(alias.asname or alias.name for alias in node.names if alias.name == "get")
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                docstrings.add(id(node.body[0].value))
        # A same-named local elsewhere in the file cannot prove a caller-supplied
        # mapping safe. Keep the unknown argument alongside known assignments.
        if isinstance(node, ast.arg):
            bindings.setdefault(node.arg, []).append(node)
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and node.value is not None:
                    bindings.setdefault(target.id, []).append(node.value)
                elif isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
                    bindings.setdefault(target.value.id, []).append(ast.Dict(
                        keys=[target.slice], values=[node.value],
                    ))
        if (isinstance(node, ast.AugAssign) and isinstance(node.op, ast.BitOr)
                and isinstance(node.target, ast.Name)):
            bindings.setdefault(node.target.id, []).append(node.value)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "update" and isinstance(node.func.value, ast.Name):
                bindings.setdefault(node.func.value.id, []).extend(node.args)
                bindings[node.func.value.id].append(ast.Dict(
                    keys=[ast.Constant(kw.arg) for kw in node.keywords],
                    values=[kw.value for kw in node.keywords],
                ))
            if (node.func.attr == "setdefault" and isinstance(node.func.value, ast.Name)
                    and node.args):
                bindings.setdefault(node.func.value.id, []).append(ast.Dict(
                    keys=[node.args[0]],
                    values=[node.args[1] if len(node.args) > 1 else ast.Constant(None)],
                ))

    def keys(expr: ast.AST, seen: frozenset[str] = frozenset()) -> set[str]:
        if isinstance(expr, ast.Name) and expr.id not in seen and expr.id in bindings:
            return set().union(*(keys(value, seen | {expr.id})
                                 for value in bindings.get(expr.id, [])))
        if isinstance(expr, ast.Dict):
            result = {unquote_plus(key.value).lower() for key in expr.keys
                      if isinstance(key, ast.Constant) and isinstance(key.value, str)}
            for key, value in zip(expr.keys, expr.values):
                if key is None:
                    result |= keys(value, seen)
                elif not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
                    result.add(UNRESOLVED_PARAMS)
            return result
        if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id == "dict":
            result = {kw.arg.lower() for kw in expr.keywords if kw.arg}
            for argument in expr.args + [kw.value for kw in expr.keywords if kw.arg is None]:
                result |= keys(argument, seen)
            return result
        if isinstance(expr, (ast.List, ast.Tuple)):
            result = set()
            for item in expr.elts:
                if (isinstance(item, (ast.List, ast.Tuple)) and len(item.elts) == 2
                        and isinstance(item.elts[0], ast.Constant)
                        and isinstance(item.elts[0].value, str)):
                    result.add(unquote_plus(item.elts[0].value).lower())
                else:
                    result.add(UNRESOLVED_PARAMS)
            return result
        if isinstance(expr, ast.IfExp):
            return keys(expr.body, seen) | keys(expr.orelse, seen)
        if isinstance(expr, ast.Constant) and expr.value is None:
            return set()
        return {UNRESOLVED_PARAMS}

    def forwarded_params(expr: ast.AST, seen: frozenset[str] = frozenset()) -> set[str]:
        """Resolve the params entry of a **kwargs mapping; unknown mappings need review."""
        if isinstance(expr, ast.Name) and expr.id not in seen and expr.id in bindings:
            return set().union(*(forwarded_params(value, seen | {expr.id})
                                 for value in bindings[expr.id]))
        if isinstance(expr, ast.Dict):
            result = set()
            for key, value in zip(expr.keys, expr.values):
                if key is None:
                    result |= forwarded_params(value, seen)
                elif isinstance(key, ast.Constant) and key.value == "params":
                    result |= keys(value)
                elif not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
                    result.add(UNRESOLVED_PARAMS)
            return result
        if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id == "dict":
            result = set()
            for keyword in expr.keywords:
                if keyword.arg == "params":
                    result |= keys(keyword.value)
                elif keyword.arg is None:
                    result |= forwarded_params(keyword.value, seen)
            for argument in expr.args:
                result |= forwarded_params(argument, seen)
            return result
        return {UNRESOLVED_PARAMS}

    sites = []

    def visit(node: ast.AST, scope: tuple[str, ...] = ()) -> None:
        if id(node) in docstrings:
            return
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            scope += (node.name,)
        parameters = set()
        unresolved_params = False
        if isinstance(node, (ast.JoinedStr, ast.Constant)):
            parts = node.values if isinstance(node, ast.JoinedStr) else [node]
            literal = "".join(part.value for part in parts
                              if isinstance(part, ast.Constant) and isinstance(part.value, str))
            parameters = {match.lower() for match in QUERY_FIELD.findall(unquote_plus(literal))}
        if isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            if name in encoders:
                arguments = node.args or [kw.value for kw in node.keywords if kw.arg == "query"]
                if arguments:
                    parameters = keys(arguments[0])
            if name in request_functions:
                for keyword in node.keywords:
                    if keyword.arg == "params":
                        parameters |= keys(keyword.value)
                    elif keyword.arg is None:
                        parameters |= forwarded_params(keyword.value)
                # Session.request(method, url, params, ...) accepts params positionally.
                is_session_request = (
                    isinstance(node.func, ast.Attribute) and name == "request"
                    and not (isinstance(node.func.value, ast.Name)
                             and node.func.value.id in requests_modules)
                )
                if is_session_request and len(node.args) > 2:
                    parameters |= keys(node.args[2])
                is_requests_get = (
                    isinstance(node.func, ast.Name) and name in positional_gets
                    or isinstance(node.func, ast.Attribute) and name == "get"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in requests_modules
                )
                if is_requests_get and len(node.args) > 1:
                    parameters |= keys(node.args[1])
                unresolved_params = UNRESOLVED_PARAMS in parameters
        parameters &= SENSITIVE
        if unresolved_params:
            parameters.add(UNRESOLVED_PARAMS)
        if parameters:
            sites.append(Site(path, node.lineno, ".".join(scope) or "<module>",
                              ast.unparse(node), tuple(sorted(parameters))))
        for child in ast.iter_child_nodes(node):
            # Literal segments are already examined with their entire f-string.
            if isinstance(node, ast.JoinedStr) and isinstance(child, ast.Constant):
                continue
            visit(child, scope)

    visit(tree)
    return sites


def scan_tree(root: Path) -> list[Site]:
    return [site for path in sorted(root.rglob("*.py"))
            for site in credential_url_sites(path.read_text(encoding="utf-8"),
                                             path.relative_to(root).as_posix())]


def unreviewed_sites(root: Path) -> list[Site]:
    return [site for site in scan_tree(root) if not ALLOWLIST.get(site.identity)]


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "siege_utilities"
    findings = unreviewed_sites(root)
    for site in findings:
        print(site)
    print(f"Credential URL guard: {len(findings)} unreviewed sites")
    return bool(findings)


if __name__ == "__main__":
    sys.exit(main())

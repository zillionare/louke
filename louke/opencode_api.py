"""OpenCode HTTP API: starlette ASGI sub-app at /api/opencode."""
from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from .opencode.in_memory import get_default_adapter


app = Starlette()


def _exists(instance_id: str) -> bool:
    return any(i.id == instance_id for i in get_default_adapter().list())


async def create_instance(request: Request):
    inst = get_default_adapter().create(correlation_id=request.headers.get("x-correlation-id", ""))
    return JSONResponse(inst.to_dict(), status_code=201)


async def list_instances(request: Request):
    return JSONResponse({"instances": [i.to_dict() for i in get_default_adapter().list()]})


async def delete_instance(request: Request):
    inst_id = request.query_params.get("id", "")
    if not inst_id:
        return JSONResponse({"error_code": "VALIDATION_ERROR", "message": "id required"},
                            status_code=400)
    inst = get_default_adapter().stop(inst_id)
    return JSONResponse(inst.to_dict())


async def send_message(request: Request):
    inst_id = request.path_params["id"]
    if not _exists(inst_id):
        return JSONResponse({"error_code": "INSTANCE_NOT_FOUND",
                             "message": f"unknown instance {inst_id}"}, status_code=404)
    body = await request.json()
    content = body.get("content", "")
    try:
        msg, accepted = get_default_adapter().send_message(
            inst_id, content, correlation_id="")
    except RuntimeError as e:
        return JSONResponse({"error_code": "INSTANCE_NOT_RUNNING", "message": str(e)},
                            status_code=409)
    return JSONResponse({"message": msg.to_dict(), "accepted": accepted}, status_code=202)


async def list_messages(request: Request):
    inst_id = request.path_params["id"]
    if not _exists(inst_id):
        return JSONResponse({"error_code": "INSTANCE_NOT_FOUND",
                             "message": f"unknown instance {inst_id}"}, status_code=404)
    after = request.query_params.get("after")
    msgs = get_default_adapter().list_messages(inst_id, after_message_id=after)
    return JSONResponse({"instance_id": inst_id, "messages": [m.to_dict() for m in msgs]})


_PREFIX = "/api/opencode"
app.add_route(f"{_PREFIX}/instances", create_instance, methods=["POST"])
app.add_route(f"{_PREFIX}/instances", list_instances, methods=["GET"])
app.add_route(f"{_PREFIX}/instances", delete_instance, methods=["DELETE"])
app.add_route(f"{_PREFIX}/instances/{{id}}/messages", send_message, methods=["POST"])
app.add_route(f"{_PREFIX}/instances/{{id}}/messages", list_messages, methods=["GET"])

# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import os
from fastapi import APIRouter, Depends, Request, Response, File, UploadFile, Form
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.concurrency import run_in_threadpool
from starlette import status as http_status
from starlette.exceptions import HTTPException
import html
from core.bucketmgr import get_s3_client
from core.exceptions import forbidden_exception, bad_file_upload_exception, invalid_file_type_exception, file_too_large_exception
from core.settings import settings
from dependencies import get_current_user
from models.general import User, UserLanguage
from services.fileutils import (MAX_FILE_SIZE, MAX_SMALL_FILE_SIZE)

router = APIRouter(
    tags=["Terms"]
)

FILES_DIR = "files"

@router.get("/api/terms")
def get_terms(request: Request,
            response: Response,
            s3_client = Depends(get_s3_client),
            ):
    lang = request.headers.get('Accept-Language')
    if (lang != UserLanguage.en.value) and (lang != UserLanguage.it.value):
        lang = UserLanguage.en.value
    response.headers["Content-Type"] = "text/markdown; charset=utf-8"
    try:
        fkey = f"terms_{lang}.md"
        obj = s3_client.get_object(
            Bucket=settings.minio_bucket_name, 
            Key=fkey)
    except Exception:
        obj = None
    if not obj:
        fname = f"terms_{lang}.md.example"
        fpath = os.path.join(FILES_DIR, fname)
        return FileResponse(fpath)
    else:
        content = obj["Body"]
        return StreamingResponse(content=content, media_type="text/markdown; charset=utf-8")

@router.post("/api/terms") # upload legal terms file (multipart/form-data)
async def upload_terms(file: UploadFile = File(...), 
        language: str = Form(...), 
        current_user: User = Depends(get_current_user),
        s3_client=Depends(get_s3_client)
    ):
    if not current_user.is_admin:
        raise forbidden_exception()
    if (file is None) or (file.filename is None) or (file.filename == ""):
        raise bad_file_upload_exception()
    if not file.filename.endswith(('.md', '.markdown')):
        raise invalid_file_type_exception()
    if file.content_type not in ["text/markdown", "text/plain"]:
        raise invalid_file_type_exception()
    content = await file.read()
    file_size = len(content)
    if file_size > MAX_SMALL_FILE_SIZE:
        raise file_too_large_exception(MAX_SMALL_FILE_SIZE)
    try:
        text_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise bad_file_upload_exception()
    safe_text = html.escape(text_content)
    lang = language
    if (lang != UserLanguage.en.value) and (lang != UserLanguage.it.value):
        lang = UserLanguage.en.value
    fname = f"terms_{lang}.md"
    try:
        await run_in_threadpool(
            lambda: s3_client.put_object(
                Body=safe_text.encode("utf-8"), 
                Bucket=settings.minio_bucket_name, 
                Key=fname,
                ContentType=file.content_type
            )
        )   
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading file to S3"
        )
    return {"message": "Terms uploaded successfully"}
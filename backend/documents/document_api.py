"""
Document API Endpoints

Provides:
- GET /documents - List accessible documents
- GET /documents/all - List all documents with access status
- GET /documents/{filename} - Get document info
- GET /documents/{filename}/download - Download/decrypt document
"""

import os
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import Response

from backend.auth.middleware import get_current_user
from backend.documents.document_service import (
    list_documents_for_tier,
    list_all_documents_with_access,
    decrypt_document,
    get_document_info
)
from backend.rbac.tier_config import PROTECTED_FOLDER, get_tier_name

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("")
async def list_my_documents(user: dict = Depends(get_current_user)):
    """
    List documents accessible to the current user.
    
    Returns only files that the user's tier level can access.
    """
    tier_level = user["tier_level"]
    documents = list_documents_for_tier(tier_level)
    
    return {
        "user_tier": tier_level,
        "tier_name": get_tier_name(tier_level),
        "folder": PROTECTED_FOLDER,
        "count": len(documents),
        "documents": documents
    }


@router.get("/all")
async def list_all_documents(user: dict = Depends(get_current_user)):
    """
    List ALL documents, showing which are accessible and restricted.
    
    Useful for showing users what they can and cannot access.
    """
    tier_level = user["tier_level"]
    result = list_all_documents_with_access(tier_level)
    
    return {
        "user_tier": tier_level,
        "tier_name": get_tier_name(tier_level),
        "accessible_count": len(result["accessible"]),
        "restricted_count": len(result["restricted"]),
        "accessible": result["accessible"],
        "restricted": result["restricted"]
    }


@router.get("/{filename}")
async def get_document(filename: str, user: dict = Depends(get_current_user)):
    """
    Get detailed information about a specific document.
    """
    tier_level = user["tier_level"]
    doc_info = get_document_info(filename, tier_level)
    
    if not doc_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{filename}' not found"
        )
    
    return doc_info


@router.get("/{filename}/download")
async def download_document(filename: str, user: dict = Depends(get_current_user)):
    """
    Download/view a document (decrypted if encrypted).
    
    Returns the file content as bytes.
    Access is checked against user's tier level.
    """
    tier_level = user["tier_level"]
    
    # Check if document exists first
    doc_info = get_document_info(filename, tier_level)
    if not doc_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{filename}' not found"
        )
    
    # Check access
    if not doc_info["accessible"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Your tier: {tier_level}. Required: {doc_info.get('requires_tier', 'higher')}"
        )
    
    # Decrypt/read the file
    content = decrypt_document(filename, tier_level)
    
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read or decrypt document"
        )
    
    # Determine content type
    display_name = doc_info["display_name"]
    if display_name.endswith('.pdf'):
        media_type = "application/pdf"
    elif display_name.endswith('.txt'):
        media_type = "text/plain"
    else:
        media_type = "application/octet-stream"
    
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'inline; filename="{display_name}"'
        }
    )

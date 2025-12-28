"""
Resource links endpoint - generates presigned URLs for key JSON reports
"""
from fastapi import APIRouter, HTTPException
from app.clients.digital_ocean_client import do_client
from botocore.client import Config
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/resource-links")
async def get_resource_links():
    """
    Generate presigned URLs for key resource files in DigitalOcean Spaces
    
    Returns:
        dict: Dictionary containing presigned URLs for:
            - client_data: Summary of all clients
            - client_kb_data: Detailed KB audit results
            - agent_directory: Complete agent registry
    """
    try:
        # URLs expire in 1 hour (3600 seconds)
        expiration = 3600
        
        links = {}
        
        # 1. Client Data (summary.json)
        try:
            links["client_data"] = do_client.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': 'mintleads-clients-kb',
                    'Key': '_client_kb_master/summary.json'
                },
                ExpiresIn=expiration
            )
        except Exception as e:
            logger.warning(f"Failed to generate link for client_data: {e}")
            links["client_data"] = None
        
        # 2. Client KB Data (client_audit_results.json)
        try:
            links["client_kb_data"] = do_client.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': 'mintleads-clients-kb',
                    'Key': '_client_kb_master/reports/client_audit_results.json'
                },
                ExpiresIn=expiration
            )
        except Exception as e:
            logger.warning(f"Failed to generate link for client_kb_data: {e}")
            links["client_kb_data"] = None
        
        # 3. Agent Directory (agent_registry.json)
        try:
            links["agent_directory"] = do_client.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': 'mintleads-agents-store',
                    'Key': 'agent_registry.json'
                },
                ExpiresIn=expiration
            )
        except Exception as e:
            logger.warning(f"Failed to generate link for agent_directory: {e}")
            links["agent_directory"] = None
        
        logger.info("Successfully generated resource links")
        return links
        
    except Exception as e:
        logger.error(f"Error generating resource links: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate resource links: {str(e)}")


@router.get("/summary-warnings")
async def get_summary_warnings():
    """
    Fetch top_warnings from the summary.json file
    
    Returns:
        dict: Contains top_warnings array from summary.json
    """
    try:
        response = do_client.s3_client.get_object(
            Bucket='mintleads-clients-kb',
            Key='_client_kb_master/summary.json'
        )
        summary_data = json.loads(response['Body'].read().decode('utf-8'))
        
        return {
            "warnings": summary_data.get("top_warnings", []),
            "generated_at": summary_data.get("generated_at")
        }
    except Exception as e:
        logger.error(f"Error fetching summary warnings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch summary warnings: {str(e)}")


@router.get("/client-details/{client_slug}")
async def get_client_details(client_slug: str):
    """
    Fetch detailed client information from both KB and agent registries
    
    Args:
        client_slug: The client identifier
        
    Returns:
        dict: Contains kb_data and agent_data for the client
    """
    try:
        result = {
            "client_slug": client_slug,
            "kb_data": None,
            "agent_data": None
        }
        
        # Fetch KB/Client data
        try:
            kb_response = do_client.s3_client.get_object(
                Bucket='mintleads-clients-kb',
                Key=f'_client_kb_master/clients/{client_slug}.json'
            )
            result["kb_data"] = json.loads(kb_response['Body'].read().decode('utf-8'))
        except Exception as e:
            logger.warning(f"Could not fetch KB data for {client_slug}: {e}")
        
        # Fetch Agent data
        try:
            agent_response = do_client.s3_client.get_object(
                Bucket='mintleads-agents-store',
                Key=f'agents/inbox_manager_{client_slug}.json'
            )
            result["agent_data"] = json.loads(agent_response['Body'].read().decode('utf-8'))
        except Exception as e:
            logger.warning(f"Could not fetch agent data for {client_slug}: {e}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching client details for {client_slug}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch client details: {str(e)}")


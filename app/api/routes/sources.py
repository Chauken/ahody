from enum import Enum
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from pydantic_ai import Agent
from app.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


class SourceType(str, Enum):
    URL = "URL"
    RSS = "RSS"


class SourceRequest(BaseModel):
    userPrompt: str
    url: str


class SourceResponse(BaseModel):
    title: str
    cronjob_expression: str
    url: str
    type: SourceType


# Create Pydantic AI agent for source configuration
source_agent = Agent(
    model=settings.WEB_SCRAPING_MODEL,
    result_type=SourceResponse,
    system_prompt="""You are an AI assistant that helps configure news source scraping schedules.
    
    Your task is to:
    1. Extract or generate a meaningful title for the news source
    2. Generate an appropriate cron expression based on the user's timing requirements
    3. Determine if the source is a URL (regular website) or RSS (RSS/XML feed)
    
    Source type detection rules:
    - If URL contains "rss", "feed", "xml" or ends with .rss, .xml: type = "RSS"
    - If URL is a regular website/news site: type = "URL"
    - Default to "URL" if uncertain
    
    Cron expression rules:
    - Parse time from user prompt (e.g., "06.00" = 6 AM, "18:30" = 6:30 PM)
    - If no specific time mentioned: "0 9 * * *" (daily at 9 AM)
    - Common patterns:
      - "every morning at 06.00": "0 6 * * *"
      - "every hour": "0 * * * *"
      - "twice daily": "0 9,18 * * *" (9 AM and 6 PM)
      - "every weekday": "0 9 * * 1-5" (9 AM Monday-Friday)
      - "weekly": "0 9 * * 1" (9 AM every Monday)
    
    Always return a valid SourceResponse with:
    - title: A descriptive title for the source
    - cronjob_expression: A valid cron expression matching the requested time
    - url: The provided URL (use exactly as given)
    - type: Either "URL" or "RSS" based on the URL analysis
    """,
)


class SourceAIService:
    async def generate_source_config(self, user_prompt: str, url: str) -> SourceResponse:
        """
        Generate source configuration using Pydantic AI based on user prompt and URL.
        """
        user_message = f"""
        User prompt: "{user_prompt}"
        URL: "{url}"
        
        Please generate the source configuration.
        """
        
        logger.info(f"Starting AI generation for URL: {url}")
        logger.info(f"User prompt: {user_prompt}")
        logger.info(f"Using model: {settings.WEB_SCRAPING_MODEL}")
        
        try:
            logger.info("Calling Pydantic AI agent...")
            result = await source_agent.run(user_message)
            
            logger.info(f"AI agent returned result: {result}")
            logger.info(f"Result data type: {type(result.data)}")
            logger.info(f"Result data: {result.data}")
            
            # Ensure the URL matches the input
            response = result.data
            response.url = url
            
            logger.info(f"Final response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"AI agent failed with error: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.exception("Full exception traceback:")
            
            # Fallback to default values if AI fails
            fallback_response = SourceResponse(
                title=f"News Source - {url}",
                cronjob_expression="0 9 * * *",  # Default: daily at 9 AM
                url=url,
                type=SourceType.URL  # Default to URL type
            )
            logger.warning(f"Using fallback response: {fallback_response}")
            return fallback_response


def get_source_ai_service() -> SourceAIService:
    return SourceAIService()


@router.post("/sources")
async def add_source(
    request: SourceRequest,
    ai_service: SourceAIService = Depends(get_source_ai_service)
) -> SourceResponse:
    """
    Add a new news source with AI-generated configuration.
    
    The AI will analyze the user prompt to:
    - Generate an appropriate title for the source
    - Create a cron expression based on timing requirements in the prompt
    - Default to daily 9 AM scraping if no specific timing is mentioned
    """
    if not request.url.startswith("http"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid URL - must start with http or https"
        )
    
    try:
        source_config = await ai_service.generate_source_config(
            request.userPrompt, 
            request.url
        )
        return source_config
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating source configuration: {str(e)}"
        )

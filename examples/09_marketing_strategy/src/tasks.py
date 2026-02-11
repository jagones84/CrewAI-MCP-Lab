from crewai import Task
from crewai import Agent

class MarketingTasks:
    """
    Tasks for the Marketing Strategy Crew.
    """
    
    def research_product(self, agent: Agent, product_description: str, output_file: str = None) -> Task:
        """
        Creates the market research task.
        
        Args:
            agent (Agent): The Market Researcher agent.
            product_description (str): Description of the product to research.
            output_file (str): Path to save the research report.
        """
        return Task(
            description=f"""
                Conduct a comprehensive market research for the following product:
                '{product_description}'
                
                Identify:
                1. Target audience demographics.
                2. Key competitors and their selling points.
                3. Current market trends relevant to this product.
                
                Use the search tools to find real-time data.
            """,
            expected_output="A detailed market research report including target audience, competitors, and trends.",
            agent=agent,
            output_file=output_file
        )

    def develop_strategy(self, agent: Agent, context: list, output_file: str = None) -> Task:
        """
        Creates the strategy development task.
        
        Args:
            agent (Agent): The Creative Strategist agent.
            context (list): List of previous tasks (research) to use as context.
            output_file (str): Path to save the strategy document.
        """
        return Task(
            description="""
                Based on the provided market research, develop a marketing strategy.
                Include:
                1. A Unique Selling Proposition (USP).
                2. Three potential marketing campaigns (e.g., Social Media, Influencer, Email).
                3. Five catchy taglines.
                4. A detailed visual description for a hero image that represents the brand.
            """,
            expected_output="A comprehensive marketing strategy document with USP, campaigns, taglines, and visual direction.",
            agent=agent,
            context=context,
            output_file=output_file
        )

    def generate_campaign_image(self, agent: Agent, context: list, output_dir: str) -> Task:
        """
        Creates the image generation task.
        
        Args:
            agent (Agent): The Visual Designer agent.
            context (list): List of previous tasks (strategy) to use as context.
            output_dir (str): Directory to save the generated image.
        """
        return Task(
            description=f"""
                Create a stunning concept image for the marketing campaign based on the visual description provided in the strategy.
                
                Steps:
                1. Extract the visual description from the strategy.
                2. Create a high-quality prompt for the image generator.
                3. Use the 'generate_image' tool to create the image.
                   - Workflow: 'default_workflow.json' (or 'image_perfectDeliberate_text_to_image_API.json' if better)
                   - Output Path: '{output_dir}'
                
                Ensure the prompt describes style, lighting, and mood.
            """,
            expected_output="A path to the generated image file and a description of the generated visual.",
            agent=agent,
            context=context
        )

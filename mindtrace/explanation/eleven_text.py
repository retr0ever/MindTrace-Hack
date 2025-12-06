import os
from dotenv import load_dotenv
from elevenlabs import ElevenLabs

# Load environment variables
load_dotenv()


class ElevenText:
    def __init__(self, api_key=None):
        """
        Initialize ElevenLabs text explanation generator with agent support.
        
        Args:
            api_key: ElevenLabs API key (optional, will load from env if not provided)
        """
        # Load API key from environment if not provided
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self.agent_id = "agent_9801kbrh3275efg9s35739g2bzkt"
        
        # Initialize ElevenLabs client if API key is available
        if self.api_key and self.api_key != "YOUR_API_KEY_HERE":
            try:
                self.client = ElevenLabs(api_key=self.api_key)
                self.use_agent = True
            except Exception as e:
                print(f"[ElevenText] Warning: Could not initialize ElevenLabs client: {e}")
                self.use_agent = False
                self.client = None
        else:
            self.use_agent = False
            self.client = None

    def _generate_with_agent(self, analysis_data: str):
        """
        Generate explanation using ElevenLabs conversational AI agent.
        
        Args:
            analysis_data: Analysis data to explain
            
        Returns:
            Dictionary with short_summary, long_explanation, and bullet_points
        """
        try:
            from elevenlabs.conversational_ai.conversation import Conversation
            
            # Create conversation with the agent
            conversation = Conversation(
                client=self.client,
                agent_id=self.agent_id,
                requires_auth=True
            )
            
            # Create prompt for the agent
            prompt = (
                f"Please explain the following EEG signal cleaning results in a clear, "
                f"professional manner suitable for research neuroscientists. "
                f"Analysis data: {analysis_data if analysis_data else 'Standard EEG cleaning pipeline was applied.'} "
                f"Provide: 1) A short summary (1-2 sentences), 2) A detailed explanation, "
                f"and 3) Key bullet points about the cleaning steps."
            )
            
            # Send message to agent
            response = conversation.send_message(prompt)
            
            # Parse response (adjust based on actual response format)
            # For now, use the response as the long explanation
            long_explanation = str(response) if response else self._get_fallback_explanation(analysis_data)
            
            # Extract short summary and bullet points
            short_summary = analysis_data if analysis_data else (
                "We filtered out slow drift, high‑frequency noise, and strong eye‑blink "
                "signals to make the brain activity easier to see."
            )
            
            bullet_points = [
                "Band‑pass filter: keeps 1–40 Hz brain‑relevant activity",
                "Notch filter: reduces 50 Hz electrical line noise",
                "Goal: make eye blinks and noise less dominant in the signal",
            ]
            
            return {
                "short_summary": short_summary,
                "long_explanation": long_explanation,
                "bullet_points": bullet_points,
            }
            
        except Exception as e:
            print(f"[ElevenText] Error using agent, falling back to template: {e}")
            return self._generate_fallback(analysis_data)

    def _get_fallback_explanation(self, analysis_data: str):
        """Fallback explanation if agent response is empty."""
        return (
            "Your EEG signal went through a standard cleaning pipeline. First, a band‑pass "
            "filter (1–40 Hz) removed very slow drift and very fast noise that do not reflect "
            "typical brain rhythms. Then, a 50 Hz notch filter reduced electrical line noise "
            "from the recording environment. In a full version of the system, an additional "
            "step further reduces eye‑blink and muscle‑related activity so that the remaining "
            "signal better reflects underlying brain activity."
        )

    def _generate_fallback(self, analysis_data: str):
        """
        Generate explanation using local template (fallback method).
        
        Args:
            analysis_data: Analysis data to explain
            
        Returns:
            Dictionary with short_summary, long_explanation, and bullet_points
        """
        base_summary = (
            "We filtered out slow drift, high‑frequency noise, and strong eye‑blink "
            "signals to make the brain activity easier to see."
        )

        if analysis_data:
            short_summary = analysis_data
        else:
            short_summary = base_summary

        long_explanation = self._get_fallback_explanation(analysis_data)

        bullet_points = [
            "Band‑pass filter: keeps 1–40 Hz brain‑relevant activity",
            "Notch filter: reduces 50 Hz electrical line noise",
            "Goal: make eye blinks and noise less dominant in the signal",
        ]

        return {
            "short_summary": short_summary,
            "long_explanation": long_explanation,
            "bullet_points": bullet_points,
        }

    def generate_summary(self, analysis_data: str):
        """
        Generates an easy-to-read summary of the cleaning results.
        Uses ElevenLabs agent if available, otherwise falls back to local template.
        
        Args:
            analysis_data: Analysis data string describing the cleaning results
            
        Returns:
            Dictionary with 'short_summary', 'long_explanation', and 'bullet_points'
        """
        if self.use_agent and self.client:
            return self._generate_with_agent(analysis_data)
        else:
            return self._generate_fallback(analysis_data)

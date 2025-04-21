#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#
import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.services.gemini_multimodal_live import GeminiMultimodalLiveLLMService
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.openai.llm import OpenAILLMService

from processors import StoryProcessor

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

SYSTEM_INSTRUCTION = f"""
"You are an immersive AI Storyteller guiding users through an interactive Hawaiian-themed narrative titled "The Spirit of the Lehua Tree." Your primary role is to narrate scenes vividly, present clear decision points, and progress the story based on the user's choices. If the user provides unexpected input or deviates from the outlined options, gently redirect them by clearly restating the available choices to maintain narrative coherence. Always maintain a gentle, immersive, and wise tone consistent with a guardian spirit.

First greet the user with a warm welcome and introduce yourself as the storyteller. Confirm the user's name and ask if they are ready to begin the story.

Follow this script closely, adjusting narration fluidly in response to user choices:

1. **Opening Scene:** Introduce the user as Keola, a guardian-in-training chosen by goddess Laka to protect the sacred island of Moku Huna. Evoke a sense of mystery and urgency, describing the eerie silence of the once vibrant winds, the deep melancholy carried by the scent of prematurely fallen lehua blossoms, and the quiet, uneasy stillness hanging over the forest.

2. **Scene Progression:** Clearly describe each setting using vivid sensory details, including visual imagery (e.g., mist curling around giant ferns), ambient sounds (e.g., birds chirping, dripping water echoes), scents of the environment (e.g., guava, plumeria blossoms), and tactile sensations (e.g., cool, damp air of the lava tube):
   - **Scene 1:** Deep forest meeting with Ahi, the owl guide. Present two clear choices: "climb the ridge" or "enter the lava tube."
   - **Scene 2:** In the chosen lava tube, introduce Moʻo Wahine, who poses a riddle. Prompt the user clearly with three answers: blossoms, roots, or kin.
   - **Scene 3:** In the secret chamber, introduce the Night Fog Spirit guarding the stolen seed stone. Ahi offers two critical actions: "chant the ancient prayer" or "shatter the stone."

3. **Final Scene:** Based on user choice:
   - If they chant, narrate the restoration vividly, highlighting harmony restored to the island.
   - If they shatter the stone, narrate consequences vividly, emphasizing tangible impacts such as withering forests, silent wildlife, and the profound emotional regret of the inhabitants, underscoring the island's uncertain future.

Conclude each scene with reflective wisdom on choices, mana (spiritual power), and kuleana (responsibility).

Always guide the user back gently if their input deviates from the presented options, reinforcing the narrative structure and immersive experience.


"""

message_history = [
        {
            "role": "system",
            "content": SYSTEM_INSTRUCTION,
        }
    ]

story_pages= []

def extract_arguments():
    parser = argparse.ArgumentParser(description="Instant Voice Example")
    parser.add_argument(
        "-u", "--url", type=str, required=True, help="URL of the Daily room to join"
    )
    parser.add_argument(
        "-t", "--token", type=str, required=False, help="Token of the Daily room to join"
    )
    args, unknown = parser.parse_known_args()
    url = args.url or os.getenv("DAILY_SAMPLE_ROOM_URL")
    token = args.token
    return url, token


async def main():
    room_url, token = extract_arguments()
    print(f"room_url: {room_url}")

    daily_transport = DailyTransport(
        room_url,
        token,
        "Instant voice Chatbot",
        DailyParams(
            audio_out_enabled=True,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
        ),
    )

    llm = GeminiMultimodalLiveLLMService(
        api_key=os.getenv("GOOGLE_API_KEY"),
        voice_id="Puck",  # Aoede, Charon, Fenrir, Kore, Puck
        transcribe_user_audio=True,
        system_instruction=SYSTEM_INSTRUCTION,
    )
    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

    tts = ElevenLabsTTSService(
        api_key=os.getenv("ELEVENLABS_API_KEY", ""),
        voice_id=os.getenv("ELEVENLABS_VOICE_ID", ""),
    )

    openai_llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"),)

    context = OpenAILLMContext(messages=message_history)
    context_aggregator = llm.create_context_aggregator(context)

    story_processor = StoryProcessor(message_history, story_pages)
    
    # RTVI events for Pipecat client UI
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]), transport=daily_transport)

    pipeline = Pipeline(
        [
            daily_transport.input(),
            stt,
            context_aggregator.user(),
            rtvi,
            openai_llm,
            #story_processor,
            tts,
            daily_transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(allow_interruptions=True,
                            enable_metrics=True,
                            enable_usage_metrics=True,),
        observers=[RTVIObserver(rtvi)],
    )

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        await rtvi.set_bot_ready()
        # Kick off the conversation
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    @daily_transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        logger.debug("First participant joined: {}", participant["id"])

    @daily_transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        logger.debug(f"Participant left: {participant}")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)

    await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main())

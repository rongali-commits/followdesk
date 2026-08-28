from __future__ import annotations

import asyncio
import re
import subprocess
import sys
import textwrap
from datetime import timedelta
from pathlib import Path

SHARED_PYDEPS = Path(__file__).resolve().parents[3] / "tmp" / "upwork-video" / "pydeps"
sys.path.insert(0, str(SHARED_PYDEPS))

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parents[1]
ASSETS = ROOT / "sales-assets"
OUTPUT = ASSETS / "FollowDesk-Upwork-Demo.mp4"
SILENT_OUTPUT = ASSETS / "FollowDesk-Upwork-Demo-Silent.mp4"
NARRATION = ASSETS / "FollowDesk-Upwork-Narration.mp3"
SUBTITLES = ASSETS / "FollowDesk-Upwork-Narration.srt"
WIDTH = 1280
HEIGHT = 720
FPS = 30
INK = "#181727"
PRIMARY = "#5b4df7"
ACCENT = "#dfff70"
WHITE = "#ffffff"
MUTED = "#aaa8b8"
VOICE = "en-US-GuyNeural"
NARRATION_TEXT = (
    "Meet FollowDesk, a focused lead follow-up system for service businesses. "
    "Capture every enquiry through a branded form with the customer and service details your team needs. "
    "Each lead appears in one dashboard, with its status, priority, owner, and next action clearly organized. "
    "Move opportunities through a simple pipeline, from new enquiry to booked customer or won business. "
    "FollowDesk sends approved follow-up messages on schedule, so your team responds consistently without manual chasing. "
    "Customize the brand, sender details, booking link, and workflow for each business. "
    "Choose your package and launch FollowDesk with Noerong."
)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / name), size)


def title_frame(outro: bool = False) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), INK)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((75, 67, 135, 127), radius=17, fill=PRIMARY)
    draw.text((96, 75), "F", font=font(34, True), fill=WHITE, anchor="ma")
    draw.text((153, 77), "FOLLOWDESK", font=font(21, True), fill=WHITE)
    draw.rounded_rectangle((75, 178, 280, 213), radius=18, fill=ACCENT)
    draw.text(
        (177, 195),
        "WHITE-LABEL PRODUCT",
        font=font(13, True),
        fill="#293600",
        anchor="mm",
    )
    if outro:
        headline = "Ready to stop losing leads?"
        support = "A focused follow-up and booking system for service businesses."
        action = "FollowDesk by Noerong"
    else:
        headline = "Turn every enquiry\ninto a clear next step."
        support = "Lead capture, timed follow-up, booking, and a focused pipeline."
        action = "See the complete workflow in 42 seconds"
    draw.multiline_text(
        (75, 255), headline, font=font(55, True), fill=WHITE, spacing=7
    )
    draw.text((78, 405), support, font=font(23), fill=MUTED)
    draw.rounded_rectangle((75, 510, 520, 580), radius=35, fill=PRIMARY)
    draw.text((297, 545), action, font=font(18, True), fill=WHITE, anchor="mm")
    draw.ellipse((1110, 75, 1370, 335), fill="#26243a")
    draw.ellipse((1050, 470, 1190, 610), fill="#324000")
    return image


def screenshot_frame(filename: str, label: str, headline: str) -> Image.Image:
    source = Image.open(ASSETS / filename).convert("RGB")
    source = source.resize((1088, 680), Image.Resampling.LANCZOS)
    image = Image.new("RGB", (WIDTH, HEIGHT), "#f4f3f8")
    image.paste(source.crop((0, 0, 1088, 610)), (96, 82))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((96, 23, 205, 59), radius=18, fill=ACCENT)
    draw.text((150, 41), label.upper(), font=font(12, True), fill="#2d3c00", anchor="mm")
    draw.text((224, 27), headline, font=font(24, True), fill=INK)
    draw.rounded_rectangle((96, 82, 1184, 692), radius=20, outline="#d8d5e3", width=2)
    return image


def srt_time(value: timedelta) -> str:
    total_ms = int(value.total_seconds() * 1000)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1_000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def grouped_subtitles(cues: list[object], words_per_cue: int = 18) -> str:
    source_sentences = [
        sentence.split()
        for sentence in re.split(r"(?<=[.!?])\s+", NARRATION_TEXT.strip())
    ]
    groups: list[tuple[list[object], list[str]]] = []
    cursor = 0
    for sentence_words in source_sentences:
        sentence_cues = cues[cursor : cursor + len(sentence_words)]
        cursor += len(sentence_words)
        if len(sentence_cues) != len(sentence_words):
            break
        group_count = max(1, (len(sentence_cues) + words_per_cue - 1) // words_per_cue)
        group_size = (len(sentence_cues) + group_count - 1) // group_count
        for start in range(0, len(sentence_cues), group_size):
            groups.append(
                (
                    sentence_cues[start : start + group_size],
                    sentence_words[start : start + group_size],
                )
            )

    if cursor != len(cues):
        groups = [
            (cues[start : start + words_per_cue], [cue.content for cue in cues[start : start + words_per_cue]])
            for start in range(0, len(cues), words_per_cue)
        ]

    blocks: list[str] = []
    for index, (group, source_words) in enumerate(groups, start=1):
        words = " ".join(source_words)
        wrapped = "\n".join(textwrap.wrap(words, width=62, max_lines=2))
        cue_start = max(group[0].start - timedelta(milliseconds=80), timedelta())
        cue_end = group[-1].end + timedelta(milliseconds=220)
        blocks.append(
            f"{index}\n{srt_time(cue_start)} --> {srt_time(cue_end)}\n{wrapped}\n"
        )
    return "\n".join(blocks)


async def create_narration() -> None:
    dependency_dir = ROOT.parents[1] / "tmp" / "upwork-video" / "pydeps"
    sys.path.insert(0, str(dependency_dir))
    import edge_tts

    communicator = edge_tts.Communicate(
        NARRATION_TEXT,
        voice=VOICE,
        rate="+8%",
        volume="+0%",
        boundary="WordBoundary",
    )
    subtitle_maker = edge_tts.SubMaker()
    with NARRATION.open("wb") as audio_file:
        async for message in communicator.stream():
            if message["type"] == "audio":
                audio_file.write(message["data"])
            elif message["type"] == "WordBoundary":
                subtitle_maker.feed(message)
    SUBTITLES.write_text(grouped_subtitles(subtitle_maker.cues), encoding="utf-8")


def write_video() -> None:
    asyncio.run(create_narration())
    scenes = [
        (title_frame(), 4.0),
        (screenshot_frame("01-customer-form.png", "Capture", "A branded enquiry experience"), 7.0),
        (
            screenshot_frame(
                "02-lead-dashboard.png", "Organize", "Every lead and next action in one place"
            ),
            7.0,
        ),
        (screenshot_frame("03-pipeline.png", "Convert", "Move opportunities from new to won"), 7.0),
        (
            screenshot_frame(
                "04-email-sequence.png", "Follow up", "Approved messages sent on time"
            ),
            7.0,
        ),
        (
            screenshot_frame(
                "05-brand-settings.png",
                "White label",
                "The buyer controls the brand and booking link",
            ),
            5.0,
        ),
        (title_frame(outro=True), 5.0),
    ]
    executable = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        executable,
        "-y",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{WIDTH}x{HEIGHT}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-an",
        "-vcodec",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(SILENT_OUTPUT),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    if process.stdin is None:
        raise RuntimeError("Could not open the video encoder")
    fade_frames = 10
    previous: Image.Image | None = None
    try:
        for scene, duration in scenes:
            if previous is not None:
                for index in range(1, fade_frames + 1):
                    frame = Image.blend(previous, scene, index / fade_frames)
                    process.stdin.write(frame.tobytes())
            frame_count = max(1, int(duration * FPS) - (fade_frames if previous else 0))
            payload = scene.tobytes()
            for _ in range(frame_count):
                process.stdin.write(payload)
            previous = scene
    finally:
        process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError("Video encoding failed")
    subtitle_path = SUBTITLES.name
    subtitle_filter = (
        "subtitles=filename='"
        + subtitle_path
        + "':force_style='FontName=Segoe UI,FontSize=12,PrimaryColour=&H00FFFFFF,"
        "BackColour=&H9A181727,OutlineColour=&H9A181727,BorderStyle=3,Outline=1,"
        "Shadow=0,MarginL=90,MarginR=90,MarginV=24,Alignment=2'"
    )
    final_command = [
        executable,
        "-y",
        "-i",
        str(SILENT_OUTPUT),
        "-i",
        str(NARRATION),
        "-vf",
        subtitle_filter,
        "-af",
        "loudnorm=I=-16:LRA=11:TP=-1.5,apad=pad_dur=5",
        "-t",
        "42",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "19",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-movflags",
        "+faststart",
        str(OUTPUT),
    ]
    subprocess.run(final_command, cwd=ASSETS, check=True)
    SILENT_OUTPUT.unlink(missing_ok=True)
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    write_video()

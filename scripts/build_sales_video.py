from __future__ import annotations

import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parents[1]
ASSETS = ROOT / "sales-assets"
OUTPUT = ASSETS / "FollowDesk-Upwork-Demo.mp4"
WIDTH = 1280
HEIGHT = 720
FPS = 30
INK = "#181727"
PRIMARY = "#5b4df7"
ACCENT = "#dfff70"
WHITE = "#ffffff"
MUTED = "#aaa8b8"


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


def write_video() -> None:
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
        str(OUTPUT),
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
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    write_video()

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

SHARED_PYDEPS = Path(__file__).resolve().parents[3] / "tmp" / "upwork-video" / "pydeps"
sys.path.insert(0, str(SHARED_PYDEPS))

import edge_tts
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
WORK = WORKSPACE / "tmp" / "followdesk-video"
FRAMES = WORK / "frames"
ASSETS = ROOT / "sales-assets"
OUTPUT = ASSETS / "FollowDesk-Upwork-Demo.mp4"
NARRATION = ASSETS / "FollowDesk-Upwork-Narration.mp3"
SUBTITLES = ASSETS / "FollowDesk-Upwork-Narration.srt"
FRAMES.mkdir(parents=True, exist_ok=True)

WIDTH, HEIGHT = 1280, 720
BG = "#0B0F0D"
PANEL = "#171E1A"
CREAM = "#F6F4ED"
MUTED = "#A8B1AB"
LIME = "#DFFF70"
PURPLE = "#7567FF"
FONT_REGULAR = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_SEMIBOLD = Path(r"C:\Windows\Fonts\seguisb.ttf")
VOICE = "en-US-EmmaMultilingualNeural"
NARRATION_TEXT = """Turn every enquiry into a clear next step with FollowDesk.

FollowDesk gives service businesses a branded lead capture and follow-up workflow.

Customers submit their details through a focused enquiry form designed for action.

Each lead appears in a private dashboard with status, priority, owner, and next action.

Move opportunities through the sales pipeline from new enquiry to booked customer.

Send approved follow-up messages on schedule, and customize the brand, booking link, and workflow.

Choose your package and launch FollowDesk for your business with Noerong."""


def font(size: int, semibold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_SEMIBOLD if semibold else FONT_REGULAR), size)


def rounded_panel(canvas: Image.Image, box: tuple[int, int, int, int], radius: int = 26) -> None:
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    x1, y1, x2, y2 = box
    shadow_draw.rounded_rectangle(
        (x1 + 8, y1 + 12, x2 + 8, y2 + 12), radius, fill=(0, 0, 0, 115)
    )
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(14)))
    ImageDraw.Draw(canvas).rounded_rectangle(
        box, radius, fill=PANEL, outline="#303A34", width=2
    )


def brand_header(canvas: Image.Image, label: str) -> None:
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((48, 28, 88, 68), 12, fill=PURPLE)
    draw.text((61, 33), "F", font=font(24, True), fill=CREAM)
    draw.text((102, 31), "FollowDesk", font=font(25, True), fill=CREAM)
    pill_width = draw.textbbox((0, 0), label.upper(), font=font(15, True))[2] + 34
    draw.rounded_rectangle(
        (WIDTH - 48 - pill_width, 32, WIDTH - 48, 64),
        16,
        fill="#1D2A23",
        outline="#33433A",
    )
    draw.text(
        (WIDTH - 48 - pill_width + 17, 38),
        label.upper(),
        font=font(15, True),
        fill=LIME,
    )


def fit_scene(source: Path, target: Path, label: str) -> None:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), BG)
    brand_header(canvas, label)
    box = (38, 84, WIDTH - 38, HEIGHT - 34)
    rounded_panel(canvas, box)

    shot = Image.open(source).convert("RGB")
    fitted = ImageOps.fit(
        shot,
        (1168, 574),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.46),
    )
    x = (WIDTH - fitted.width) // 2
    y = 100 + (574 - fitted.height) // 2
    mask = Image.new("L", fitted.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, fitted.width, fitted.height), 18, fill=255
    )
    canvas.paste(fitted, (x, y), mask)
    canvas.convert("RGB").save(target, quality=95)


def make_title(target: Path) -> None:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(canvas)
    for x in range(0, WIDTH, 80):
        draw.line((x, 0, x, HEIGHT), fill="#121916", width=1)
    for y in range(0, HEIGHT, 80):
        draw.line((0, y, WIDTH, y), fill="#121916", width=1)

    draw.rounded_rectangle((70, 72, 116, 118), 14, fill=PURPLE)
    draw.text((84, 78), "F", font=font(26, True), fill=CREAM)
    draw.text((132, 76), "FOLLOWDESK", font=font(23, True), fill=CREAM)
    draw.rounded_rectangle((70, 175, 250, 215), 20, fill="#18251E", outline="#35473D")
    draw.ellipse((89, 189, 101, 201), fill=LIME)
    draw.text((113, 183), "LIVE PRODUCT", font=font(16, True), fill=LIME)

    draw.text((70, 255), "Turn every enquiry", font=font(58, True), fill=CREAM)
    draw.text((70, 323), "into a clear next step.", font=font(58, True), fill=LIME)
    draw.text(
        (72, 421),
        "Lead capture, timed follow-up, booking, and a focused pipeline",
        font=font(27),
        fill=MUTED,
    )

    pills = ["BRANDED CAPTURE", "FOLLOW-UP", "BOOKING"]
    x = 70
    for pill in pills:
        width = draw.textbbox((0, 0), pill, font=font(15, True))[2] + 38
        draw.rounded_rectangle(
            (x, 512, x + width, 552), 20, fill=PANEL, outline="#35473D"
        )
        draw.text((x + 19, 520), pill, font=font(15, True), fill="#D7DED9")
        x += width + 14

    canvas.convert("RGB").save(target, quality=95)


def make_dashboard(target: Path) -> None:
    source = Image.open(ASSETS / "02-lead-dashboard.png").convert("RGB")
    cropped = ImageOps.fit(
        source,
        (WIDTH, HEIGHT),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )
    canvas = cropped.convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((930, 24, 1234, 66), 21, fill="#0F1713", outline="#314239")
    draw.ellipse((951, 39, 963, 51), fill=LIME)
    draw.text((975, 32), "PRIVATE LEAD DASHBOARD", font=font(14, True), fill=CREAM)
    canvas.convert("RGB").save(target, quality=95)


def make_outro(target: Path) -> None:
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((920, -140, 1320, 260), fill="#171B35")
    draw.ellipse((-160, 520, 240, 920), fill="#222A18")

    draw.rounded_rectangle((70, 70, 116, 116), 14, fill=PURPLE)
    draw.text((84, 76), "F", font=font(26, True), fill=CREAM)
    draw.text((132, 74), "FOLLOWDESK", font=font(23, True), fill=CREAM)

    draw.text((70, 213), "Stop losing leads", font=font(58, True), fill=CREAM)
    draw.text((70, 281), "after the first enquiry.", font=font(58, True), fill=LIME)
    draw.text(
        (72, 388),
        "Lead capture  •  Follow-up  •  Booking  •  Clear pipeline",
        font=font(27),
        fill=MUTED,
    )

    draw.rounded_rectangle((70, 490, 470, 558), 34, fill=LIME)
    draw.text(
        (108, 507),
        "CHOOSE A PACKAGE TO START",
        font=font(20, True),
        fill="#102016",
    )
    canvas.convert("RGB").save(target, quality=95)


async def create_narration() -> None:
    communicator = edge_tts.Communicate(
        NARRATION_TEXT,
        voice=VOICE,
        rate="-10%",
        volume="+0%",
        boundary="SentenceBoundary",
    )
    subtitle_maker = edge_tts.SubMaker()
    with NARRATION.open("wb") as audio_file:
        async for message in communicator.stream():
            if message["type"] == "audio":
                audio_file.write(message["data"])
            elif message["type"] == "SentenceBoundary":
                subtitle_maker.feed(message)
    SUBTITLES.write_text(subtitle_maker.get_srt(), encoding="utf-8")


def render_video() -> Path:
    asyncio.run(create_narration())

    title = FRAMES / "00-title.png"
    form = FRAMES / "01-form.png"
    dashboard = FRAMES / "02-dashboard.png"
    pipeline = FRAMES / "03-pipeline.png"
    email = FRAMES / "04-email.png"
    brand = FRAMES / "05-brand.png"
    outro = FRAMES / "06-outro.png"

    make_title(title)
    fit_scene(ASSETS / "01-customer-form.png", form, "BRANDED ENQUIRY")
    make_dashboard(dashboard)
    fit_scene(ASSETS / "03-pipeline.png", pipeline, "SALES PIPELINE")
    fit_scene(ASSETS / "04-email-sequence.png", email, "TIMED FOLLOW-UP")
    fit_scene(ASSETS / "05-brand-settings.png", brand, "WHITE-LABEL SETUP")
    make_outro(outro)

    scenes = [
        (title, 3.0),
        (form, 6.5),
        (dashboard, 7.0),
        (pipeline, 6.8),
        (email, 7.0),
        (brand, 3.5),
        (outro, 7.2),
    ]

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [ffmpeg, "-y"]
    for path, duration in scenes:
        command.extend(["-loop", "1", "-t", f"{duration:.1f}", "-i", str(path)])
    command.extend(["-i", str(NARRATION)])

    filters: list[str] = []
    for index, (_, duration) in enumerate(scenes):
        fade_out = max(duration - 0.25, 0)
        filters.append(
            f"[{index}:v]fps=30,format=yuv420p,"
            f"fade=t=in:st=0:d=0.25,fade=t=out:st={fade_out:.2f}:d=0.25,"
            f"setpts=PTS-STARTPTS[v{index}]"
        )
    joined = "".join(f"[v{i}]" for i in range(len(scenes)))
    filters.append(f"{joined}concat=n={len(scenes)}:v=1:a=0[base]")
    subtitle_path = SUBTITLES.relative_to(WORKSPACE).as_posix()
    filters.append(
        "[base]subtitles=filename='"
        + subtitle_path
        + "':force_style='FontName=Segoe UI,FontSize=16,PrimaryColour=&H00FFFFFF,"
        "BackColour=&H78000000,OutlineColour=&H78000000,BorderStyle=3,Outline=1,"
        "Shadow=0,MarginL=90,MarginR=90,MarginV=18,Alignment=2'[vout]"
    )
    audio_index = len(scenes)
    filters.append(f"[{audio_index}:a]apad=pad_dur=3[aout]")

    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-t",
            "41.0",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "19",
            "-r",
            "30",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(OUTPUT),
        ]
    )
    subprocess.run(command, cwd=WORKSPACE, check=True)
    return OUTPUT


if __name__ == "__main__":
    print(render_video())

import os
import tempfile
from pathlib import Path

import gradio as gr

from audio.templates import list_templates
from content.auto import generate_lesson, groq_llm_call
from content.manual import parse_manual_input
from pipeline import run_pipeline
from render.assemble import ASPECT_SIZES

TEMPLATES_DIR = Path(__file__).parent / "config" / "templates"


def _load_templates():
    templates = list_templates(TEMPLATES_DIR)
    return {t.name: t for t in templates}


def generate_video(mode, csv_text, topic, template_name, aspect_ratios):
    """Entry point for both the Gradio UI and external API callers.

    Always returns a 3-tuple (video_9_16, video_16_9, log_text); any failure is
    reported in the log text instead of propagating a traceback to the caller.
    """
    try:
        templates = _load_templates()
        if template_name not in templates:
            valid = ", ".join(templates)
            return None, None, (
                f"Lỗi: template không hợp lệ '{template_name}'. Các template hợp lệ: {valid}."
            )
        template = templates[template_name]

        aspect_ratios = list(aspect_ratios or [])
        if not aspect_ratios:
            return None, None, (
                "Lỗi: chưa chọn tỉ lệ khung hình nào. "
                "Hãy chọn ít nhất một tỉ lệ (9:16 hoặc 16:9)."
            )
        invalid_ratios = [r for r in aspect_ratios if r not in ASPECT_SIZES]
        if invalid_ratios:
            valid = ", ".join(ASPECT_SIZES)
            return None, None, (
                f"Lỗi: tỉ lệ khung hình không hợp lệ: {', '.join(map(str, invalid_ratios))}. "
                f"Các tỉ lệ hợp lệ: {valid}."
            )

        if mode == "Nhập danh sách":
            items, errors = parse_manual_input(csv_text)
            warnings = [f"Dòng {e.line_number}: {e.message}" for e in errors]
        else:
            items = generate_lesson(topic, groq_llm_call)
            warnings = []

        if not items:
            message = "Không có mục hợp lệ để tạo video.\n" + "\n".join(warnings)
            return None, None, message

        work_dir = tempfile.mkdtemp(prefix="zhvideo_")
        result = run_pipeline(items, template, aspect_ratios, work_dir)

        log_lines = warnings + [f"Lỗi mục '{e.item.hanzi}': {e.error}" for e in result.item_errors]
        log_lines += [
            f"Lỗi dựng video ({ratio}): {msg}" for ratio, msg in result.assembly_errors.items()
        ]
        video_9_16 = result.video_paths.get("9:16")
        video_16_9 = result.video_paths.get("16:9")
        log_text = "\n".join(log_lines) if log_lines else "Hoàn tất, không có lỗi."
        return video_9_16, video_16_9, log_text
    except Exception as exc:  # noqa: BLE001 - public API must never leak a raw traceback
        return None, None, f"Lỗi: {exc}"


def build_app() -> gr.Blocks:
    templates = _load_templates()
    template_names = list(templates.keys())

    with gr.Blocks() as demo:
        gr.Markdown("# Tạo video dạy tiếng Trung song ngữ Việt-Trung")
        mode = gr.Radio(
            ["Nhập danh sách", "Chủ đề tự động"], value="Nhập danh sách", label="Chế độ nhập"
        )
        csv_text = gr.Textbox(
            label="Danh sách CSV (hanzi,pinyin,meaning_vi)",
            placeholder="你好,nǐ hǎo,xin chào\n谢谢,xiè xie,cảm ơn",
            info="Mỗi dòng một mục, theo thứ tự hanzi,pinyin,meaning_vi (không cần dòng tiêu đề).",
            lines=8,
        )
        topic = gr.Textbox(label="Chủ đề (chế độ tự động)")
        template_name = gr.Dropdown(
            template_names, value=template_names[0], label="Template trình tự audio"
        )
        aspect_ratios = gr.CheckboxGroup(
            ["9:16", "16:9"], value=["9:16"], label="Tỉ lệ khung hình"
        )
        submit = gr.Button("Tạo video")
        video_9_16 = gr.Video(label="Video 9:16")
        video_16_9 = gr.Video(label="Video 16:9")
        log = gr.Textbox(label="Log", lines=6)

        submit.click(
            generate_video,
            inputs=[mode, csv_text, topic, template_name, aspect_ratios],
            outputs=[video_9_16, video_16_9, log],
            api_name="generate_video",
        )

    return demo


if __name__ == "__main__":
    # Render (and most PaaS hosts) assign the listen port via $PORT and expect
    # the process to bind 0.0.0.0, not the Gradio default of 127.0.0.1:7860.
    port = int(os.environ.get("PORT", 7860))
    build_app().launch(server_name="0.0.0.0", server_port=port)

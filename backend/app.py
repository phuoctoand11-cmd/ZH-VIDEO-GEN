import tempfile
from pathlib import Path

import gradio as gr

from audio.templates import list_templates
from content.auto import gemini_llm_call, generate_lesson
from content.manual import parse_manual_input
from pipeline import run_pipeline

TEMPLATES_DIR = Path(__file__).parent / "config" / "templates"


def _load_templates():
    templates = list_templates(TEMPLATES_DIR)
    return {t.name: t for t in templates}


def generate_video(mode, csv_text, topic, template_name, aspect_ratios):
    templates = _load_templates()
    template = templates[template_name]

    if mode == "Nhập danh sách":
        items, errors = parse_manual_input(csv_text)
        warnings = [f"Dòng {e.line_number}: {e.message}" for e in errors]
    else:
        items = generate_lesson(topic, gemini_llm_call)
        warnings = []

    if not items:
        message = "Không có mục hợp lệ để tạo video.\n" + "\n".join(warnings)
        return None, None, message

    work_dir = tempfile.mkdtemp(prefix="zhvideo_")
    result = run_pipeline(items, template, aspect_ratios, work_dir)

    log_lines = warnings + [f"Lỗi mục '{e.item.hanzi}': {e.error}" for e in result.item_errors]
    log_lines += [f"Lỗi dựng video ({ratio}): {msg}" for ratio, msg in result.assembly_errors.items()]
    video_9_16 = result.video_paths.get("9:16")
    video_16_9 = result.video_paths.get("16:9")
    log_text = "\n".join(log_lines) if log_lines else "Hoàn tất, không có lỗi."
    return video_9_16, video_16_9, log_text


def build_app() -> gr.Blocks:
    templates = _load_templates()
    template_names = list(templates.keys())

    with gr.Blocks() as demo:
        gr.Markdown("# Tạo video dạy tiếng Trung song ngữ Việt-Trung")
        mode = gr.Radio(
            ["Nhập danh sách", "Chủ đề tự động"], value="Nhập danh sách", label="Chế độ nhập"
        )
        csv_text = gr.Textbox(label="Danh sách CSV (hanzi,pinyin,meaning_vi)", lines=8)
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
        )

    return demo


if __name__ == "__main__":
    build_app().launch()

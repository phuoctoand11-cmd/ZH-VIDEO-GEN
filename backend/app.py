import csv
import io
import os
import tempfile
from pathlib import Path

import gradio as gr

from audio.templates import list_templates
from content.auto import groq_llm_call
from content.dialogue_topic import generate_dialogue_topic
from content.manual import parse_dialogue_csv_input, parse_manual_input
from content.schema import DialogueResult, VocabCardItem, VocabTopicResult
from content.vocab_topic import generate_vocab_topic
from pipeline import run_dialogue_pipeline, run_vocab_card_pipeline
from render.assemble import ASPECT_SIZES

TEMPLATES_DIR = Path(__file__).parent / "config" / "templates"

MODES = ["Nhập danh sách", "Từ vựng theo chủ đề", "Hội thoại theo chủ đề"]
TOPIC_MODES = ["Từ vựng theo chủ đề", "Hội thoại theo chủ đề"]

# render.vocab_card.draw_vocab_card uses a fixed-height row layout with no
# per-item font-size floor, so it crashes (font size 0) once rows get too
# thin. Empirically the smallest confirmed-safe count across ASPECT_SIZES
# (manual-list mode never sets a header) is 19 items at 16:9 (1280x720) —
# fails at 20. 35 items still render fine at 9:16 (720x1280). MAX_VOCAB_ITEMS
# is set with a 3-item safety margin below the tighter (16:9) limit.
MAX_VOCAB_ITEMS = 16


def _load_templates():
    templates = list_templates(TEMPLATES_DIR)
    return {t.name: t for t in templates}


def _rows_to_csv_text(rows: list[list[str]]) -> str:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(rows)
    return buf.getvalue().strip()


def generate_preview(mode, topic):
    """Asks the LLM to draft content for a topic mode and returns it as
    editable CSV text, without rendering any video yet — the user reviews
    or edits this text, then generate_video renders from whatever ends up
    in that box (no second LLM call).

    Always returns a 2-tuple (csv_text_or_update, log_text); any failure is
    reported in the log text instead of propagating a traceback.
    """
    try:
        if not (topic or "").strip():
            return gr.update(), "Lỗi: chưa nhập chủ đề/bộ thủ."

        if mode == "Từ vựng theo chủ đề":
            vocab_result = generate_vocab_topic(topic, groq_llm_call)
            rows = [
                [item.hanzi, item.pinyin or "", item.meaning_vi] for item in vocab_result.items
            ]
            csv_text = _rows_to_csv_text(rows)
            return csv_text, 'Đã tạo xong, kiểm tra/sửa rồi bấm "Tạo video".'

        if mode == "Hội thoại theo chủ đề":
            dialogue_result = generate_dialogue_topic(topic, groq_llm_call)
            rows = [
                [turn.speaker_name, turn.line.hanzi, turn.line.pinyin or "", turn.line.meaning_vi]
                for turn in dialogue_result.turns
            ]
            csv_text = _rows_to_csv_text(rows)
            return csv_text, 'Đã tạo xong, kiểm tra/sửa rồi bấm "Tạo video".'

        return gr.update(), f"Lỗi: chế độ '{mode}' không dùng xem trước."
    except Exception as exc:  # noqa: BLE001 - public API must never leak a raw traceback
        return gr.update(), f"Lỗi: {exc}"


def generate_video(mode, csv_text, template_name, aspect_ratios, topic=""):
    """Entry point for both the Gradio UI and external API callers.

    `topic` is display-only here — it labels the vocab card's subtitle
    ("Chủ đề: {topic}") and is never sent to the LLM (that already happened,
    if at all, in generate_preview). Always returns a 3-tuple (video_9_16,
    video_16_9, log_text); any failure is reported in the log text instead
    of propagating a traceback to the caller.
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

        if mode not in MODES:
            return None, None, f"Lỗi: chế độ nhập không hợp lệ '{mode}'."

        work_dir = tempfile.mkdtemp(prefix="zhvideo_")

        if mode == "Hội thoại theo chủ đề":
            turns, errors = parse_dialogue_csv_input(csv_text or "")
            warnings = [f"Dòng {e.line_number}: {e.message}" for e in errors]
            if not turns:
                message = "Không có lượt thoại hợp lệ để tạo video.\n" + "\n".join(warnings)
                return None, None, message
            dialogue_result = DialogueResult(title="", turns=turns)
            result = run_dialogue_pipeline(dialogue_result, template, aspect_ratios, work_dir)
            log_lines = list(warnings)

        else:  # "Nhập danh sách" or "Từ vựng theo chủ đề" — both render from csv_text
            items, errors = parse_manual_input(csv_text or "")
            warnings = [f"Dòng {e.line_number}: {e.message}" for e in errors]
            if not items:
                message = "Không có mục hợp lệ để tạo video.\n" + "\n".join(warnings)
                return None, None, message
            if len(items) > MAX_VOCAB_ITEMS:
                return None, None, (
                    f"Lỗi: danh sách có {len(items)} mục, vượt quá giới hạn {MAX_VOCAB_ITEMS} "
                    "mục cho phép. Vui lòng chia nhỏ danh sách."
                )
            vocab_result = VocabTopicResult(
                items=[
                    VocabCardItem(
                        hanzi=i.hanzi, pinyin=i.pinyin, meaning_vi=i.meaning_vi, icon_prompt=i.meaning_vi
                    )
                    for i in items
                ]
            )
            topic_label = topic.strip() if (topic or "").strip() else None
            result = run_vocab_card_pipeline(
                vocab_result, template, aspect_ratios, work_dir, topic_label=topic_label
            )
            log_lines = list(warnings)

        log_lines += [f"Lỗi mục '{e.item.hanzi}': {e.error}" for e in result.item_errors]
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
        mode = gr.Radio(MODES, value=MODES[0], label="Chế độ nhập")
        csv_text = gr.Textbox(
            label="Danh sách CSV (hanzi,pinyin,meaning_vi)",
            placeholder="你好,nǐ hǎo,xin chào\n谢谢,xiè xie,cảm ơn",
            info="Mỗi dòng một mục, theo thứ tự hanzi,pinyin,meaning_vi (không cần dòng tiêu đề). "
            "Dùng cho \"Nhập danh sách\".",
            lines=8,
        )
        topic = gr.Textbox(
            label="Chủ đề / bộ thủ",
            placeholder="vd: đồ ăn, hoặc 冫 (bộ băng)",
            info="Dùng cho \"Từ vựng theo chủ đề\" và \"Hội thoại theo chủ đề\".",
        )
        preview_btn = gr.Button("Xem trước", visible=(MODES[0] in TOPIC_MODES))
        template_name = gr.Dropdown(
            template_names, value=template_names[0], label="Template trình tự audio"
        )
        aspect_ratios = gr.CheckboxGroup(["9:16", "16:9"], value=["9:16"], label="Tỉ lệ khung hình")
        submit = gr.Button("Tạo video")
        video_9_16 = gr.Video(label="Video 9:16")
        video_16_9 = gr.Video(label="Video 16:9")
        log = gr.Textbox(label="Log", lines=6)

        mode.change(
            fn=lambda m: gr.update(visible=m in TOPIC_MODES),
            inputs=[mode],
            outputs=[preview_btn],
        )

        preview_btn.click(
            generate_preview,
            inputs=[mode, topic],
            outputs=[csv_text, log],
            api_name="generate_preview",
        )

        submit.click(
            generate_video,
            inputs=[mode, csv_text, template_name, aspect_ratios, topic],
            outputs=[video_9_16, video_16_9, log],
            api_name="generate_video",
        )

    return demo


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    build_app().launch(server_name="0.0.0.0", server_port=port)

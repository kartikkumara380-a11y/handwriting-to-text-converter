import streamlit as st
from PIL import Image
from google import genai
from pdf2image import convert_from_bytes
import time

# --- SECURE CONFIGURATION ---
api_key = st.secrets["GOOGLE_API_KEY"]

st.set_page_config(
    page_title="Handwritten Note Digitizer Pro",
    page_icon="📝",
    layout="centered"
)

st.title("📝 Handwritten Note & PDF Digitizer")

uploaded_file = st.file_uploader(
    "Choose a note image or PDF file...",
    type=["jpg", "jpeg", "png", "pdf"]
)

if uploaded_file is not None:

    is_pdf = uploaded_file.name.lower().endswith(".pdf")

    # --- PREVIEW ---
    if not is_pdf:
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        st.image(
            image,
            caption="Uploaded Sample",
            use_container_width=True
        )
    else:
        st.info(f"📁 PDF Document detected: {uploaded_file.name}")

    with st.spinner("Analyzing document..."):

        try:
            client = genai.Client(api_key=api_key)

            prompt = """
            You are an expert handwriting transcription system.

            Transcribe the handwritten text exactly as accurately as possible.

            Rules:
            - Preserve the original wording.
            - Do not summarize or explain.
            - Do not add information that is not present.
            - Preserve headings, paragraphs, bullet points, and numbering where possible.
            - If a word is unclear, make your best interpretation based on the handwriting and context.
            - Do not describe the image.
            - Output only the transcribed text.
            """

            # --- PREPARE IMAGES ---
            images_to_process = []

            if is_pdf:
                uploaded_file.seek(0)

                images_to_process = convert_from_bytes(
                    uploaded_file.read()
                )

                # Optional safety limit
                if len(images_to_process) > 10:
                    st.error(
                        "Please upload a PDF with 10 pages or fewer."
                    )
                    st.stop()

            else:
                images_to_process.append(image)

            # --- PROCESS PAGES ---
            final_text_outputs = []

            for i, img in enumerate(images_to_process):

                if is_pdf:
                    st.text(
                        f"Reading Page {i + 1} "
                        f"of {len(images_to_process)}..."
                    )

                for attempt in range(3):

                    try:
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=[img, prompt]
                        )

                        page_text = response.text
                        break

                    except Exception as e:

                        error_message = str(e)

                        if (
                            ("503" in error_message or
                             "429" in error_message)
                            and attempt < 2
                        ):
                            time.sleep(10)
                            continue

                        raise e

                if is_pdf:
                    final_text_outputs.append(
                        f"--- Page {i + 1} ---\n"
                        f"{page_text}\n"
                    )
                else:
                    final_text_outputs.append(page_text)

                # Delay between PDF pages
                if is_pdf and i < len(images_to_process) - 1:
                    time.sleep(2)

            # --- FINAL RESULT ---
            final_text = "\n".join(final_text_outputs)

            st.success("Analysis Complete!")

            st.text_area(
                "Extracted Digital Text:",
                value=final_text,
                height=400
            )

            # --- DOWNLOAD ---
            st.download_button(
                label="📥 Download Text File",
                data=final_text,
                file_name="digitized_notes.txt",
                mime="text/plain"
            )

        except Exception as e:

            st.error(f"An error occurred: {e}")

            st.info(
                "If this is a PDF-related error, make sure "
                "'poppler-utils' is included in packages.txt "
                "and the app has been redeployed."
            )

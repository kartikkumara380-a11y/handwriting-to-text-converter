import streamlit as st
from PIL import Image
from google import genai
import io
from pdf2image import convert_from_bytes

# --- SECURE CONFIGURATION ---
# Use the exact key name you saved in Streamlit Secrets
api_key = st.secrets["GOOGLE_API_KEY"]

st.set_page_config(page_title="Handwritten Note Digitizer Pro", page_icon="📝", layout="centered")
st.title("📝 Handwritten Note & PDF Digitizer")

uploaded_file = st.file_uploader("Choose a note image or PDF file...", type=["jpg", "jpeg", "png", "pdf"])

if uploaded_file is not None:
    is_pdf = uploaded_file.name.lower().endswith('.pdf')
    
    if not is_pdf:
        uploaded_file.seek(0)
        st.image(Image.open(uploaded_file), caption="Uploaded Sample", use_container_width=True)
    else:
        st.info(f"📁 PDF Document detected: {uploaded_file.name}")

    with st.spinner("Analyzing document..."):
        try:
            client = genai.Client(api_key=api_key)
            prompt = "You are an expert handwriting decoder. Transcribe all text..."
            
            images_to_process = []
            if is_pdf:
                uploaded_file.seek(0)
                # convert_from_bytes works automatically once poppler-utils is installed via packages.txt
                images_to_process = convert_from_bytes(
                    uploaded_file.read(),
                    poppler_path=r"C:\Users\user\Downloads\Release-26.02.0-0\poppler-26.02.0\Library\bin"
                )
            else:
                images_to_process.append(Image.open(uploaded_file))
                
            # Process each page with Gemini safely
            import time  # Import Python's built-in timer tool
                
            final_text_outputs = []
            for i, img in enumerate(images_to_process):
                if is_pdf:
                    st.text(f"Reading Page {i+1} of {len(images_to_process)}...")
                        
                # Try sending the page, and retry if the server gets overwhelmed
                for attempt in range(3):
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=[img, prompt]
                        )
                        page_text = response.text
                        break  # Success! Break the retry loop
                    except Exception as e:
                        if "503" in str(e) and attempt < 2:
                            time.sleep(10)  # Wait 10 seconds and try again
                            continue
                        else:
                            raise e  # If it still fails, show the error
                    
                if is_pdf:
                    final_text_outputs.append(f"--- Page {i+1} ---\n{page_text}\n")
                else:
                    final_text_outputs.append(page_text)
                    
                # --- THE IMPORTANT FIX ---
                # Take a mandatory 2-second break between pages to protect your free API key
                if is_pdf and i < len(images_to_process) - 1:
                    time.sleep(2)
                
            final_text = "\n".join(final_text_outputs)
            st.success("Analysis Complete!")
                
            # Display the text inside an editable text area
            st.text_area("Extracted Digital Text:", value=final_text, height=400)
                
            # Create a download button for a clean .txt file export
            st.download_button(
                label="📥 Download Text File",
                data=final_text,
                file_name="digitized_notes.txt",
                mime="text/plain"
            )
                
        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.info("Note: If you are getting a 'poppler' error on Windows, ensure poppler is installed and its path is configured in the script.")

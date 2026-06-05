import streamlit as st
from PIL import Image
from google import genai
import io
from pdf2image import convert_from_bytes

# Set up the web page title and icon
st.set_page_config(page_title="Handwritten Note Digitizer Pro", page_icon="📝", layout="centered")

st.title("📝 Handwritten Note & PDF Digitizer")
st.write("Upload an image or a PDF of your notes to convert them into clean digital text.")

# Sidebar for the API Key
st.sidebar.title("Configuration")
api_key = st.sidebar.text_input("Enter Gemini API Key:", type="password")
st.sidebar.markdown("[Get a free API key here](https://aistudio.google.com/)")

# Optional: If you downloaded poppler for Windows, paste the path to the 'bin' folder here.
# Example: r"C:\poppler\Library\bin"
POPPLER_PATH = r"C:\Users\user\Downloads\Release-26.02.0-0\poppler-26.02.0\Library\bin"

# Update the file uploader widget to accept PDF as well
uploaded_file = st.file_uploader(
    "Choose a note image or PDF file...", 
    type=["jpg", "jpeg", "png", "pdf"]
)

if uploaded_file is not None:
    # Check the file type
    is_pdf = uploaded_file.name.lower().endswith('.pdf')
    
    # Display preview
    if not is_pdf:
        image_preview = Image.open(uploaded_file)
        st.image(image_preview, caption="Uploaded Handwriting Sample", use_container_width=True)
    else:
        st.info(f"📁 PDF Document detected: {uploaded_file.name}")

    if not api_key:
        st.warning("⚠️ Please enter your Gemini API key in the left sidebar to process the document.")
    else:
        # Show a loading spinner while the AI works
        with st.spinner("Analyzing document structure and transcribing handwriting..."):
            try:
                # Initialize the official GenAI client
                client = genai.Client(api_key=api_key)
                
                # Define the prompt
                prompt = (
                    "You are an expert handwriting decoder. Transcribe all text found in this document. "
                    "If the text is part of a diagram, flowchart, or boxes, organize the transcribed text "
                    "logically with clear headings, bullet points, or markdown formatting so it makes sense to a reader."
                )
                
                # List to hold images to process
                images_to_process = []
                
                if is_pdf:
                    # Convert PDF bytes into a list of PIL Images
                    # If on Windows and you set POPPLER_PATH, add: poppler_path=POPPLER_PATH
                    pdf_bytes = uploaded_file.read()
                    pages = convert_from_bytes(pdf_bytes, poppler_path=POPPLER_PATH)
                    images_to_process.extend(pages)
                    st.write(f"Processing {len(pages)} page(s) from PDF...")
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
                                time.sleep(5)  # Wait 5 seconds and try again
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
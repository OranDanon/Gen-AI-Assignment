import streamlit as st
from io import BytesIO
import logging
import json
import ocr_processor
import convertor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="מערכת ניתוח הטפסים של הביטוח הלאומי", layout="wide")
st.title("מערכת ניתוח הטפסים של הביטוח הלאומי")

# Add sidebar with information
with st.sidebar:
    st.header("מידע על המערכת")
    st.write("מערכת זו מאפשרת ניתוח אוטומטי של טפסי ביטוח לאומי.")
    st.write("המערכת משתמשת בטכנולוגיית OCR ובינה מלאכותית לחילוץ נתונים מהטפסים.")
    st.write("הנתונים מוצגים בפורמט JSON מובנה.")

file_to_analyze = st.file_uploader("אנא העלה את הקובץ שלך", type=["pdf", "jpg", "jpeg", "png"])

if file_to_analyze is not None:
    try:
        # Display file info
        st.write(f"File name: {file_to_analyze.name}, Size: {file_to_analyze.size} bytes")

        # Create tabs for different views
        tab1, tab2 = st.tabs(["תוצאות", "JSON מלא"])

        with st.spinner('אנא המתן, אני מעבד את הטופס..'):
            # Process the file
            progress_bar = st.progress(0)

            # OCR Processing
            st.text("מבצע OCR...")
            progress_bar.progress(25)
            file_bytes = file_to_analyze.getvalue()
            file_buffer = BytesIO(file_bytes)
            file_buffer.name = file_to_analyze.name
            ocr_result = ocr_processor.process(file_buffer)

            # Data Extraction
            st.text("מחלץ נתונים...")
            progress_bar.progress(75)
            resulted_json = convertor.text_to_json(ocr_result)
            progress_bar.progress(100)

            # Parse JSON for display
            json_data = json.loads(resulted_json)

            # Display in tabs
            with tab1:
                st.subheader("נתונים שחולצו מהטופס")

                # Display key information in a more readable format
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**פרטי התובע:**")
                    st.write(f"שם: {json_data.get('firstName', '')} {json_data.get('lastName', '')}")
                    st.write(f"מספר זהות: {json_data.get('idNumber', '')}")
                    st.write(f"מגדר: {json_data.get('gender', '')}")

                    if 'dateOfBirth' in json_data:
                        dob = json_data['dateOfBirth']
                        st.write(f"תאריך לידה: {dob.get('day', '')}/{dob.get('month', '')}/{dob.get('year', '')}")

                with col2:
                    st.write("**פרטי התאונה:**")
                    if 'dateOfInjury' in json_data:
                        doi = json_data['dateOfInjury']
                        st.write(f"תאריך פגיעה: {doi.get('day', '')}/{doi.get('month', '')}/{doi.get('year', '')}")
                    st.write(f"שעת פגיעה: {json_data.get('timeOfInjury', '')}")
                    st.write(f"סוג עבודה: {json_data.get('jobType', '')}")
                    st.write(f"מקום התאונה: {json_data.get('accidentLocation', '')}")
                    st.write(f"כתובת התאונה: {json_data.get('accidentAddress', '')}")

                st.write("**תיאור התאונה:**")
                st.write(json_data.get('accidentDescription', ''))

                st.write("**איבר שנפגע:**")
                st.write(json_data.get('injuredBodyPart', ''))

            with tab2:
                st.subheader("JSON מלא")
                st.json(resulted_json)

            st.text("הושלם")
    except Exception as e:
        st.error(f"שגיאה בעיבוד הקובץ: {str(e)}")
        logger.error(f"Processing error: {str(e)}", exc_info=True)
        st.write("נא לוודא שהקובץ תקין וניתן לקריאה.")

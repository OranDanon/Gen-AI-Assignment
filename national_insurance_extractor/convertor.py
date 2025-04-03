import logging
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
import config
import pydantic_models
from azure.core.exceptions import AzureError
from langchain_openai import AzureChatOpenAI

logger = logging.getLogger(__name__)

field_extractor_system_prompt = """
You are an expert document extraction system specialized in National Insurance Institute forms.
Your task is to extract specific fields from the form and format them according to the provided JSON schema.
If you are uncertain about a value, leave it empty rather than making a guess or filling it with incorrect data.
Be precise and follow the exact JSON structure provided.

Here is an example input and expected JSON output:

Example Input:
# Text File
המוסד לביטוח לאומי
מינהל הגמלאות
בקשה למתן טיפול רפואי
לנפגע עבודה - עצמאי
אל קופ״ח/ביה״ח_ מאיר כפס
נא עיין בדברי ההסבר שבעמוד 2 לפני מילוי הטופס
תאריך קבלת הטופס בקופה
02021999
שנה חודש יום
עמוד 1 מתוך 2
תאריך מילוי הטופס
25012023
שנה חודש יום
1
תאריך הפגיעה
16042022
שנה חודש יום
2
פרטי התובע
שם משפחה
שם פרטי
ת. ז.
ס״ב
יהודה
טננהוים
מין
זכר
נקבה
02021995
שנה חודש יום
כתובת
רחוב / תא דואר
מס׳ בית
כניסה
דירה
יישוב
מיקוד
הרמבם
16
1
12
אבן יהודה
312422
טלפון קווי
ח
טלפון נייד
6502474947
פרטי התאונה
3
אני מבקש לקבל עזרה רפואית בגין פגיעה בעבודה שארעה לי
מלצרות
כאשר עבדתי ב
19:00
בשעה
16.04.2022
סוג העבודה
בתאריך
תאונה בדרך ללא רכב
אחר
ת. דרכים בדרך לעבודה/מהעבודה
כתובת מקום התאונה
הורדים 8, תל אביב
החלקתי בגלל שהרצפה הייתה רטובה ולא היה שום שלט שמזהיר.
נסיבות הפגיעה / תאור התאונה
האיבר שנפגע יד שמאל
4
הצהרה
אני החתום מטה מצהיר כי אני רשום במוסד כעובד עצמאי וכי כל הפרטים שמסרתי לעיל הם נכונים ומלאים.
ידוע לי שמסירת פרטים לא נכונים או העלמת נתונים מהווים עבירה על החוק.
ידוע לי שאם התביעה לא תוכר ע״י המוסד לביטוח לאומי - קופת החולים רשאית לחייב אותי בהוצאות הטיפול
הרפואי.
שם המבקש
טננהוים יהודה
חתימהX
5
למילוי ע״י המוסד הרפואי
לאומית
מכבי
מאוחדת
כללית
הנפגע חבר בקופת חולים
הנפגע אינו חבר בקופת חולים
מהות התאונה (אבחנות רפואיות):
בל/ 283 (05.2010)
טופס זה מנוסח בלשון זכר אך פונה לנשים וגברים כאחד
תאריך לידה
8775245631
במפעל
מקום התאונה:
ת. דרכים בעבודה
# MarkDown File
<figure>
</figure>


המוסד לביטוח לאומי
מינהל הגמלאות

בקשה למתן טיפול רפואי
לנפגע עבודה - עצמאי
אל קופ״ח/ביה״ח_ מאיר כפס
נא עיין בדברי ההסבר שבעמוד 2 לפני מילוי הטופס

תאריך קבלת הטופס בקופה
02021999
שנה חודש יום

<!-- PageHeader="עמוד 1 מתוך 2" -->

תאריך מילוי הטופס

25012023
שנה חודש יום


# 1

תאריך הפגיעה

16042022

שנה חודש יום

2

פרטי התובע
שם משפחה

שם פרטי

ת. ז.
ס״ב

יהודה

טננהוים

מין

☒
זכר

☐

נקבה

02021995
שנה חודש יום


<table>
<tr>
<th colspan="6">כתובת</th>
</tr>
<tr>
<th>רחוב / תא דואר</th>
<th>מס׳ בית</th>
<th>כניסה</th>
<th>דירה</th>
<th>יישוב</th>
<th>מיקוד</th>
</tr>
<tr>
<td>הרמבם</td>
<td>16</td>
<td>1</td>
<td>12</td>
<td>אבן יהודה</td>
<td>312422</td>
</tr>
</table>


טלפון קווי

ח

טלפון נייד
6502474947

פרטי התאונה
3

אני מבקש לקבל עזרה רפואית בגין פגיעה בעבודה שארעה לי

מלצרות

כאשר עבדתי ב
19:00
בשעה
16.04.2022

סוג העבודה

בתאריך
תאונה בדרך ללא רכב
☐
אחר
☐
ת. דרכים בדרך לעבודה/מהעבודה
☐

כתובת מקום התאונה

הורדים 8, תל אביב

החלקתי בגלל שהרצפה הייתה רטובה ולא היה שום שלט שמזהיר.

נסיבות הפגיעה / תאור התאונה

האיבר שנפגע יד שמאל


# 4


## הצהרה

אני החתום מטה מצהיר כי אני רשום במוסד כעובד עצמאי וכי כל הפרטים שמסרתי לעיל הם נכונים ומלאים.
ידוע לי שמסירת פרטים לא נכונים או העלמת נתונים מהווים עבירה על החוק.
ידוע לי שאם התביעה לא תוכר ע״י המוסד לביטוח לאומי - קופת החולים רשאית לחייב אותי בהוצאות הטיפול
הרפואי.

שם המבקש

טננהוים יהודה

חתימהX


## 5 למילוי ע״י המוסד הרפואי

☐
לאומית
☐
מכבי
☒
מאוחדת
☐
כללית

☐
הנפגע חבר בקופת חולים
☐
הנפגע אינו חבר בקופת חולים
☐
מהות התאונה (אבחנות רפואיות):

<!-- PageFooter="בל/ 283 (05.2010)" -->
<!-- PageFooter="טופס זה מנוסח בלשון זכר אך פונה לנשים וגברים כאחד" -->

תאריך לידה

8775245631

במפעל
☒
מקום התאונה:

☐

ת. דרכים בעבודה


Ground truth in json format:
{{
  "lastName": "טננהוים",
  "firstName": "יהודה",
  "idNumber": "8775245631",
  "gender": "זכר",
  "dateOfBirth": {{"day": "02", "month": "02", "year": "1999"}},
  "address": {{"street": "הרמבם", "houseNumber": "16", "entrance": "1", "apartment": "12", "city": "אבן יהודה", "postalCode": "312422", "poBox": ""}},
  "landlinePhone": "",
  "mobilePhone": "0502474947",
  "jobType": "מלצרות",
  "dateOfInjury": {{"day": "16", "month": "04", "year": "2022"}},
  "timeOfInjury": "19:00",
  "accidentLocation": "במפעל",
  "accidentAddress": "הורדים 8, תל אביב",
  "accidentDescription": "החלקתי בגלל שהרצפה הייתה רטובה ולא היה שום שלט שמזהיר.",
  "injuredBodyPart": "יד שמאל",
  "signature": "",
  "formFillingDate": {{"day": "25", "month": "01", "year": "2023"}},
  "formReceiptDateAtClinic": {{"day": "02", "month": "02", "year": "1999"}},
  "medicalInstitutionFields": {{"healthFundMember": "מאוחדת","natureOfAccident": "","medicalDiagnoses": ""}}
}}
"""

def setup_parser():
    """Initialize the Pydantic parser"""
    try:
        parser = PydanticOutputParser(pydantic_object=pydantic_models.ExtractedData)
        logger.info("Pydantic parser initialized successfully")
        return parser
    except Exception as e:
        logger.error(f"Failed to initialize parser: {str(e)}")
        raise

def create_prompt(parser):
    """Create the prompt template with system and user instructions"""
    try:
        template = f"""{field_extractor_system_prompt}
{{format_instructions}}
{{query}}
"""
        prompt = PromptTemplate(
            template=template,
            input_variables=["query"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        logger.info("Prompt template created successfully")
        return prompt
    except Exception as e:
        logger.error(f"Failed to create prompt template: {str(e)}")
        raise


def initialize_client():
    """Initialize the AzureOpenAI client"""
    try:
        client = AzureChatOpenAI(
            azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
            api_key=config.AZURE_OPENAI_API_KEY,
            api_version=config.AZURE_OPENAI_API_VERSION,
            model="gpt-4o",
            temperature=0.0,
            timeout=30,
        )
        logger.info("AzureOpenAI client initialized successfully")
        return client
    except ValueError as e:
        logger.error(f"ValueError creating AzureOpenAI client: {str(e)}")
        raise ValueError(f"Error creating AzureOpenAI client: {e}")
    except AzureError as e:
        logger.error(f"AzureError creating AzureOpenAI client: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating AzureOpenAI client: {str(e)}")
        raise


def create_chain(prompt, model, parser):
    """Create the processing chain"""
    try:
        chain = prompt | model | parser
        logger.info("Processing chain created successfully")
        return chain
    except Exception as e:
        logger.error(f"Failed to create processing chain: {str(e)}")
        raise

parser = setup_parser()
model = initialize_client()
prompt = create_prompt(parser)

def text_to_json(txt):
    """Main execution function"""
    try:
        globals_list = ['prompt', 'model', 'parser']
        for required in globals_list:
            if required not in globals():
                logger.warning(f"{required} not defined in global scope")
                raise ValueError(f"{required} instance is not defined")

        chain = prompt | model | parser
        extracted_pydantic_obj = chain.invoke({"query": txt})
        return extracted_pydantic_obj.model_dump_json(indent=2)

    except Exception as e:
        logger.error(f"Main execution failed: {str(e)}")
        raise

# Average fill accuracy per document, i.e, out of all possible fields are many are not empty
# Average completion rate per each field, i.e., for each field consider how many times it is not empty divided by the number of json documents
# Overall Accuracy, out of all computed jsons how many are fully completed
# Should implement how many fields are comp out of all relevant fields
# Precision: out of those complitaed what is there average confidence
# For each field how much we succeded to fill
# how many document are fully correct
# avg accuracy per document
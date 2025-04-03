import logging

from pydantic import BaseModel, Field, field_validator

# Configure the logger
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')

class CommonBaseModel(BaseModel):
    @field_validator("*", mode="before")
    def strip_or_empty(cls, value):
        """Strip leading and trailing whitespace from string values or return empty string if None."""
        try:
            if value is None:
                logging.debug("Received None value; converting to empty string.")
                return ""
            if isinstance(value, str):
                return value.strip()
            return value
        except Exception as e:
            # Log potential unexpected errors during stripping
            logging.error(f"Error while stripping value: {e}")
            raise

class DateData(CommonBaseModel):
    day: str = Field(description="Day of the month (two digits)")
    month: str = Field(description="Month of the year (two digits)")
    year: str = Field(description="Full year, e.g. 1990")

class Address(CommonBaseModel):
    street: str = Field(description="Street name")
    houseNumber: str = Field(description="House number")
    entrance: str = Field(description="Entrance number or label")
    apartment: str = Field(description="Apartment number")
    city: str = Field(description="City or village name")
    postalCode: str = Field(description="Postal/ZIP code")
    poBox: str = Field(description="Box number if applicable, otherwise empty string")

class MedicalInstitutionFields(CommonBaseModel):
    """
    This class holds fields specific to medical institution data.
    For example, it captures health fund membership, the nature of the accident, 
    and any relevant medical diagnoses.
    """
    healthFundMember: str = Field(
        description="Use MarkDown to find a mark attached to the following possible Health Fund:  e.g. כללית, מאוחדת, מכבי, לאומית"
    )
    natureOfAccident: str = Field(
        description="A description or classification of the accident's nature"
    )
    medicalDiagnoses: str = Field(
        description="One or more relevant medical diagnoses"
    )

class ExtractedData(CommonBaseModel):
    lastName: str = Field(description="Last name")
    firstName: str = Field(description="First name")
    idNumber: str = Field(description="Israeli ID number (9 digits): ס״ב")
    gender: str = Field(description="Gender")
    dateOfBirth: DateData = Field(default_factory=DateData, description="Date of birth details")
    address: Address = Field(default_factory=Address, description="Complete address details")
    landlinePhone: str = Field(description="Landline phone number, no Hebrew char")
    mobilePhone: str = Field(
        description="Mobile phone number, usually starts with 05. If the OCR confuses 0 with 6, correct it to 0.") # fixing ocr 6 to 0
    jobType: str = Field(description="Type of job or occupation")
    dateOfInjury: DateData = Field(default_factory=DateData, description="Date of the injury")
    timeOfInjury: str = Field(description="Time of the injury")
    accidentLocation: str = Field(description="""
            Use MarkDown to find a mark attached to the following possible accident locations:
            - 'במפעל' 
            - 'ת. דרכים בעבודה' 
            - 'ת. דרכים בדרך לעבודה/מהעבודה'
            - 'תאונה בדרך ללא רכב'
            - 'אחר' (other, free text required if selected).

            If the text does not match any of the listed options, return empty string.
        """)
    accidentAddress: str = Field(description="Address where the accident occurred")
    accidentDescription: str = Field(description="Short description of how the accident occurred")
    injuredBodyPart: str = Field(description="Injured body part(s)")
    signature: str = Field(description="Signature (e.g., digital or handwritten)")
    formFillingDate: DateData = Field(default_factory=DateData, description="Date the form was filled out")
    formReceiptDateAtClinic: DateData = Field(default_factory=DateData, description="Date the form was received at the clinic")
    medicalInstitutionFields: MedicalInstitutionFields = Field(
        default_factory=MedicalInstitutionFields,
        description="Information to be filled out by the medical institution"
    )

    @field_validator("idNumber", mode="before")
    def validate_id_number(cls, value):
        """Ensure the ID number contains only digits."""
        try:
            if value and not value.isdigit():
                raise ValueError("ID number must contain only digits.")
        except ValueError as e:
            logging.error(f"Validation error for 'idNumber': {e}")
            raise
        return value
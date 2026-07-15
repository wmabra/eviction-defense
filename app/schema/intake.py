"""Pydantic models for the intake questionnaire."""
from datetime import date
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class PreScreen(BaseModel):
    """Pre-payment eligibility check."""
    state: str = Field(default="FL", description="State of eviction case")
    county: str = Field(..., description="Florida county")
    is_tenant: bool = Field(..., description="Is the user the named tenant?")
    is_residential: bool = Field(..., description="Is this a residential property?")
    received_court_papers: bool = Field(..., description="Has the user been served with summons/complaint?")
    has_writ_or_sheriff: bool = Field(default=False, description="Has a writ of possession been issued?")
    is_section_8: bool = Field(default=False, description="Is this Section 8 / public housing?")
    is_active_military: bool = Field(default=False, description="Is the user on active military duty?")
    has_bankruptcy: bool = Field(default=False, description="Has the user filed for bankruptcy?")
    has_documents_to_upload: bool = Field(default=True, description="Does the user have eviction documents ready?")


class PreScreenResult(BaseModel):
    eligible: bool
    ineligibility_reason: Optional[str] = None
    message: str


class PersonalInfo(BaseModel):
    full_name: str = Field(..., description="Full legal name")
    also_known_as: Optional[str] = None
    co_tenants: Optional[list[str]] = None
    property_address: str
    property_city: str
    property_zip: str
    county: str
    phone: str
    email: EmailStr
    mailing_address: Optional[str] = None


class LandlordInfo(BaseModel):
    landlord_name: str
    landlord_address: Optional[str] = None
    landlord_phone: Optional[str] = None
    landlord_email: Optional[str] = None
    landlord_attorney_name: Optional[str] = None
    landlord_attorney_email: Optional[str] = None
    property_manager: Optional[str] = None
    management_company: Optional[str] = None


class CaseDetails(BaseModel):
    case_number: str
    court_name: str
    court_location: Optional[str] = None
    received_3day_notice: bool = False
    notice_received_date: Optional[date] = None
    notice_amount_demanded: Optional[float] = None
    received_summons: bool = True
    summons_service_date: Optional[date] = None
    summons_service_method: Optional[str] = None  # in_person, posted, mail, other
    complaint_amount_claimed: Optional[float] = None
    court_date: Optional[date] = None
    response_deadline: Optional[date] = None
    has_attorney: bool = False


class RentPayment(BaseModel):
    monthly_rent: float
    rent_due_day: int = Field(ge=1, le=31)
    agree_with_amount: bool = True
    amount_tenant_believes_owed: Optional[float] = None
    why_disagree: Optional[str] = None
    paid_after_notice: bool = False
    amount_paid_after_notice: Optional[float] = None
    date_paid: Optional[date] = None
    has_proof_of_payment: bool = False
    sent_7day_repair_notice: bool = False
    repair_notice_date: Optional[date] = None
    repair_notice_details: Optional[str] = None
    landlord_response_to_repair: Optional[str] = None
    applied_for_rental_assistance: bool = False
    rental_assistance_status: Optional[str] = None  # pending, approved, denied
    rental_assistance_amount: Optional[float] = None


class DefenseItem(BaseModel):
    checked: bool = False
    explanation: Optional[str] = None


class Defenses(BaseModel):
    def_repairs: DefenseItem = DefenseItem()
    def_amount: DefenseItem = DefenseItem()
    def_attempted_pay: DefenseItem = DefenseItem()
    def_paid: DefenseItem = DefenseItem()
    def_waived: DefenseItem = DefenseItem()
    def_retaliation: DefenseItem = DefenseItem()
    def_fair_housing: DefenseItem = DefenseItem()
    def_accepted_rent: DefenseItem = DefenseItem()
    def_corrected: DefenseItem = DefenseItem()
    def_not_owner: DefenseItem = DefenseItem()
    def_bad_notice: DefenseItem = DefenseItem()
    def_other: DefenseItem = DefenseItem()


class Preferences(BaseModel):
    needs_more_time: bool = False
    hardship_reason: Optional[str] = None
    wants_payment_plan: bool = False
    payment_plan_amount: Optional[float] = None
    trial_by: str = "judge"  # judge or jury
    needs_filing_fee_waiver: bool = False
    has_eviction_defense_attorney: bool = False
    additional_notes: Optional[str] = None
    # Motions
    needs_continuance: bool = False
    continuance_reason: Optional[str] = None
    needs_emergency_stay: bool = False
    emergency_stay_reason: Optional[str] = None
    facing_writ_possession: bool = False
    filing_bankruptcy: bool = False
    bankruptcy_case_number: Optional[str] = None
    bankruptcy_court: Optional[str] = None
    bankruptcy_chapter: Optional[str] = None
    bankruptcy_filing_date: Optional[str] = None
    bankruptcy_attorney_name: Optional[str] = None
    bankruptcy_attorney_phone: Optional[str] = None
    bankruptcy_attorney_email: Optional[str] = None


class FinancialInfo(BaseModel):
    """Financial information for fee waiver applications (all 20 states)."""
    # Income
    monthly_gross_income: Optional[float] = None
    monthly_net_income: Optional[float] = None
    employment_income: Optional[float] = None
    self_employment_income: Optional[float] = None
    social_security_income: Optional[float] = None
    ssi_income: Optional[float] = None
    unemployment_income: Optional[float] = None
    pension_income: Optional[float] = None
    disability_income: Optional[float] = None
    veterans_benefits: Optional[float] = None
    child_support_income: Optional[float] = None
    alimony_income: Optional[float] = None
    other_income: Optional[float] = None
    other_income_description: Optional[str] = None
    
    # Expenses
    rent_or_mortgage: Optional[float] = None
    utilities_expense: Optional[float] = None
    food_expense: Optional[float] = None
    transportation_expense: Optional[float] = None
    medical_expense: Optional[float] = None
    child_care_expense: Optional[float] = None
    debt_payments: Optional[float] = None
    other_expenses: Optional[float] = None
    total_monthly_expenses: Optional[float] = None
    
    # Assets
    cash_on_hand: Optional[float] = None
    checking_balance: Optional[float] = None
    savings_balance: Optional[float] = None
    vehicle_make_model: Optional[str] = None
    vehicle_value: Optional[float] = None
    vehicle_loan_owed: Optional[float] = None
    owns_real_estate: bool = False
    real_estate_value: Optional[float] = None
    real_estate_loan_owed: Optional[float] = None
    other_assets_description: Optional[str] = None
    other_assets_value: Optional[float] = None
    
    # Household
    household_adults: int = 1
    household_children: int = 0
    total_dependents: int = 0
    
    # Public benefits (checkbox-style)
    receives_public_benefits: bool = False
    receives_snap: bool = False
    receives_ssi: bool = False
    receives_medicaid: bool = False
    receives_tanf: bool = False
    receives_section8: bool = False
    receives_public_housing: bool = False
    receives_county_assistance: bool = False
    receives_energy_assistance: bool = False
    receives_veterans_benefits: bool = False
    receives_child_care_assistance: bool = False
    
    # Additional
    unable_to_pay_fees: bool = True
    has_requested_fee_waiver_before: bool = False
    previous_fee_waiver_case: Optional[str] = None


class CompleteIntake(BaseModel):
    """All intake sections together."""
    personal_info: PersonalInfo
    landlord_info: LandlordInfo
    case_details: CaseDetails
    rent_payment: RentPayment
    defenses: Defenses
    preferences: Preferences
    financial_info: Optional[FinancialInfo] = None

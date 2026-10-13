
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from database import engine
from models import Customer, Invoice
from schemas import (
    CustomerCreate,
    CustomerResponse,
    InvoiceCreate,
    InvoiceResponse,
)

app = FastAPI(title="CashFlow Sentinel API")




def get_db():
    with Session(engine) as db:
        yield db


@app.get("/")
def home():
    return {
        "message": "CashFlow Sentinel API is running!",
        "status": "success"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "project": "CashFlow Sentinel"
    }


@app.post("/customers", response_model=CustomerResponse, status_code=201)
def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db)
):
    if customer.email:
        existing_customer = (
            db.query(Customer)
            .filter(Customer.email == str(customer.email))
            .first()
        )

        if existing_customer:
            raise HTTPException(
                status_code=409,
                detail="A customer with this email already exists."
            )

    new_customer = Customer(
        name=customer.name,
        email=str(customer.email) if customer.email else None,
        phone=customer.phone,
        business_name=customer.business_name
    )

    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)

    return new_customer


@app.get("/customers", response_model=list[CustomerResponse])
def list_customers(db: Session = Depends(get_db)):
    return db.query(Customer).order_by(Customer.id).all()


@app.post("/invoices", response_model=InvoiceResponse, status_code=201)
def create_invoice(
    invoice: InvoiceCreate,
    db: Session = Depends(get_db)
):
    customer = db.get(Customer, invoice.customer_id)

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found."
        )

    if invoice.due_date < invoice.issue_date:
        raise HTTPException(
            status_code=422,
            detail="Due date cannot be earlier than issue date."
        )

    existing_invoice = (
        db.query(Invoice)
        .filter(Invoice.invoice_number == invoice.invoice_number)
        .first()
    )

    if existing_invoice:
        raise HTTPException(
            status_code=409,
            detail="Invoice number already exists."
        )

    new_invoice = Invoice(**invoice.model_dump())

    db.add(new_invoice)
    db.commit()
    db.refresh(new_invoice)

    return new_invoice


@app.get("/invoices", response_model=list[InvoiceResponse])
def list_invoices(db: Session = Depends(get_db)):
    return db.query(Invoice).order_by(Invoice.id).all()


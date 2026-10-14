
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date

from database import engine
from models import Customer, Invoice, Payment
from schemas import (
    CustomerCreate,
    CustomerResponse,
    InvoiceCreate,
    InvoiceResponse,
    PaymentCreate,
    PaymentResponse,
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

@app.post("/payments", response_model=PaymentResponse, status_code=201)
def create_payment(
    payment: PaymentCreate,
    db: Session = Depends(get_db)
):
    invoice = db.get(Invoice, payment.invoice_id)

    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found."
        )

    total_paid = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.invoice_id == payment.invoice_id)
        .scalar()
    )

    remaining_balance = invoice.amount - total_paid

    if payment.amount > remaining_balance:
        raise HTTPException(
            status_code=422,
            detail="Payment exceeds the remaining invoice balance."
        )

    new_payment = Payment(**payment.model_dump())

    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)

    return new_payment
@app.get("/invoices/{invoice_id}/balance")
def get_invoice_balance(
    invoice_id: int,
    db: Session = Depends(get_db)
):
    invoice = db.get(Invoice, invoice_id)

    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found."
        )

    total_paid = (
        db.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(Payment.invoice_id == invoice_id)
        .scalar()
    )

    balance = invoice.amount - total_paid

    if balance == 0:
        status = "paid"
    elif total_paid > 0:
        status = "partially_paid"
    else:
        status = "unpaid"

    return {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "invoice_amount": invoice.amount,
        "total_paid": total_paid,
        "remaining_balance": balance,
        "status": status
    }
@app.get("/invoices/overdue")
def list_overdue_invoices(db: Session = Depends(get_db)):
    today = date.today()
    invoices = (
        db.query(Invoice)
        .filter(Invoice.due_date < today)
        .order_by(Invoice.due_date)
        .all()
    )

    overdue_invoices = []

    for invoice in invoices:
        total_paid = (
            db.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(Payment.invoice_id == invoice.id)
            .scalar()
        )

        balance = invoice.amount - total_paid

        if balance > 0:
            overdue_invoices.append({
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "customer_id": invoice.customer_id,
                "due_date": invoice.due_date,
                "remaining_balance": balance,
                "days_overdue": (today - invoice.due_date).days
            })

    return overdue_invoices

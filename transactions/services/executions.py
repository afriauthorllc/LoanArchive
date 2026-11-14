import json
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError
from loans.models import Loan
from transactions.models import Repayment
from django.shortcuts import render, get_object_or_404, redirect

@login_required
def create_repayment(request, loan_id):
    loan = get_object_or_404(Loan, pk=loan_id)
    if request.method == 'POST':
        try:
            raw_book = request.POST.get('book_number','').strip()
            # book_number is PositiveIntegerField - TEMP- string will crash clean()
            try:
                book_number = int(raw_book)
            except (ValueError, TypeError):
                messages.error(request, 'Book number must be a number')
                return redirect('loans:detail', pk=loan.pk)

            Repayment.objects.create(
                book_number=book_number,
                loan=loan,
                amount_paid=Decimal(request.POST.get('amount_paid','0')),
                payment_mode=request.POST.get('payment_mode','CASH'),
                collected_by=request.user
            )
            messages.success(request, 'Payment Recorded!')
        except ValidationError as e:
            messages.error(request, '; '.join([str(v) for v in e.message_dict.values()][0]) if hasattr(e, 'message_dict') else str(e))
        except Exception as e:
            messages.error(request, str(e))
    return redirect('loans:detail', pk=loan.pk)

@login_required
@require_POST
def bulk_repayment_submit(request):
    try:
        payload = json.loads(request.body)
        repayments = payload.get('repayments', [])
        
        if not repayments:
            return JsonResponse({'success': False, 'error': 'No repayments sent'}, status=400)

        saved = 0
        total = Decimal('0')
        errors = []
        breakdown = []
        created_ids = []
        today = timezone.now().date()

        with transaction.atomic():
            for item in repayments:
                try:
                    loan_id = item.get('loan_id')
                    raw_amount = item.get('amount') or item.get('amount_paid')
                    raw_book = str(item.get('book_number','')).strip()
                    
                    if not loan_id or not raw_amount:
                        raise ValueError('Missing loan_id or amount')
                    if not raw_book:
                        raise ValueError('Book number is required')

                    # FIXED: book_number is PositiveIntegerField, not CharField
                    try:
                        book_number = int(raw_book)
                    except ValueError:
                        raise ValueError(f'Book "{raw_book}" must be a number')
                    
                    amount = Decimal(str(raw_amount))
                    if amount <= 0:
                        raise ValueError('Amount must be > 0')

                    # FIXED: Loan PK is ID, not id - use pk=
                    try:
                        loan = Loan.objects.select_related('client', 'branch').get(pk=int(loan_id))
                    except Loan.DoesNotExist:
                        raise ValueError(f'Loan {loan_id} not found')

                    client_name = getattr(loan.client, 'full_name', str(loan.client)) if hasattr(loan, 'client') else f"Book {book_number}"

                    # FIXED: duplicate is per branch + per day, not global
                    # Model clean() will also enforce this, this is just early friendly error
                    if Repayment.objects.filter(
                        branch=loan.branch,
                        collection_date=today,
                        book_number=book_number
                    ).exists():
                        raise ValueError(f'Book #{book_number} already used today in {loan.branch}')

                    repayment = Repayment.objects.create(
                        book_number=book_number,
                        loan=loan,
                        amount_paid=amount,
                        payment_mode=item.get('payment_mode', 'CASH'),
                        collected_by=request.user
                    )
                    # FIXED: PK is ID (capital), not id - pk always works
                    created_ids.append(repayment.pk)
                    
                    saved += 1
                    total += amount
                    breakdown.append({
                        'client': client_name,
                        'amount': float(amount),
                        'book_number': book_number,
                    })

                except (InvalidOperation, ValueError) as e:
                    errors.append(f"Book {item.get('book_number')}: {str(e)}")
                except ValidationError as e:
                    # From Repayment.clean() - e.g. amount > balance, duplicate book
                    if hasattr(e, 'message_dict'):
                        msg = '; '.join([f"{k}: {', '.join(v)}" for k, v in e.message_dict.items()])
                    else:
                        msg = str(e)
                    errors.append(f"Book {item.get('book_number')}: {msg}")
                except Exception as e:
                    errors.append(f"Book {item.get('book_number')}: {str(e)}")

        if saved == 0:
            return JsonResponse({
                'success': False,
                'error': errors[0] if errors else 'No payments saved',
                'errors': errors,
                'ids': [],
            }, status=400)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({
                'success': True,
                'saved': saved,
                'total': float(total),
                'total_formatted': f"{total:,.0f}",
                'message': f'{saved} payments recorded • UGX {total:,.0f} total',
                'breakdown': breakdown,
                'ids': created_ids,
                'errors': errors
            })
        
        messages.success(request, f'{saved} payments recorded • UGX {total:,.0f} total')
        return JsonResponse({'success': True, 'saved': saved, 'ids': created_ids})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
            
@login_required
def edit_repayment(request, pk):
    payment = get_object_or_404(Repayment.objects.select_related('loan', 'loan__client'), pk=pk)
    loan = payment.loan
    
    max_allowed = loan.outstanding_balance + payment.amount_paid

    if request.method == 'POST':
        book_number_raw = request.POST.get('book_number', '').strip()
        amount_paid_raw = request.POST.get('amount_paid', '').strip()

        if not book_number_raw:
            messages.error(request, "Book number is required")
        else:
            try:
                book_number = int(book_number_raw)
            except ValueError:
                messages.error(request, "Book number must be a number")
                book_number = None

            # FIXED: duplicate is per branch + today, not global
            if book_number is not None and Repayment.objects.filter(
                branch=payment.branch,
                collection_date=payment.collection_date,
                book_number=book_number
            ).exclude(pk=payment.pk).exists():
                messages.error(request, f"Book #{book_number} already used today!")
            elif book_number is not None:
                try:
                    amount_paid = int(amount_paid_raw)
                    if amount_paid <= 0:
                        raise ValueError
                    if amount_paid > max_allowed:
                        messages.error(request, f"Amount exceeds max allowed UGX {max_allowed}")
                    else:
                        payment.book_number = book_number
                        payment.amount_paid = amount_paid
                        payment.save()
                        messages.success(request, f"Payment #{book_number} updated")
                        return redirect('loans:view_payments')
                except ValueError:
                    messages.error(request, "Invalid amount")
                except ValidationError as e:
                    messages.error(request, str(e))

    context = {
        'repayment': payment,
        'loan': loan,
        'max_allowed': max_allowed,
    }
    return render(request, 'loans/edit_payments.html', context)
    
    
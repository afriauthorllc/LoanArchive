import json
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction
from django.contrib import messages
from loans.models import Loan
from transactions.models import Repayment
from django.shortcuts import render, get_object_or_404, redirect

@login_required
def create_repayment(request, loan_id):
    loan = get_object_or_404(Loan, pk=loan_id)
    if request.method == 'POST':
        try:
            Repayment.objects.create(book_number=request.POST.get('book_number','').strip() or f"TEMP-{loan_id}", loan=loan, amount_paid=Decimal(request.POST.get('amount_paid','0')), payment_mode=request.POST.get('payment_mode','CASH'), collected_by=request.user)
            messages.success(request, 'Payment Recorded!')
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
        breakdown = []  # for your success modal
        created_ids = []  # <-- 1. NEW: collect IDs for View Receipts

        with transaction.atomic():
            for item in repayments:
                try:
                    loan_id = item.get('loan_id')
                    raw_amount = item.get('amount') or item.get('amount_paid')
                    
                    if not loan_id or not raw_amount:
                        raise ValueError('Missing loan_id or amount')
                    
                    amount = Decimal(str(raw_amount))
                    if amount <= 0:
                        raise ValueError('Amount must be > 0')

                    # Fetch for breakdown display
                    loan = None
                    client_name = "Client"
                    try:
                        from loans.models import Loan
                        loan = Loan.objects.select_related('client').get(id=loan_id)
                        client_name = getattr(loan.client, 'full_name', str(loan.client)) if hasattr(loan, 'client') else f"Book {item.get('book_number')}"
                    except:
                        pass

                    # <-- 2. CHANGED: capture the created object
                    repayment = Repayment.objects.create(
                        book_number=str(item.get('book_number','')).strip(),
                        loan_id=loan_id,
                        amount_paid=amount,
                        payment_mode=item.get('payment_mode', 'CASH'),
                        collected_by=request.user
                    )
                    created_ids.append(repayment.id)  # <-- 3. NEW: save its ID
                    
                    saved += 1
                    total += amount
                    breakdown.append({
                        'client': client_name,
                        'amount': float(amount),
                        'book_number': str(item.get('book_number','')).strip(),
                    })

                except (InvalidOperation, ValueError) as e:
                    errors.append(f"Book {item.get('book_number')}: {str(e)}")
                except Exception as e:
                    errors.append(f"Book {item.get('book_number')}: {str(e)}")

        # If AJAX - this is what your toast + modal will use
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
            return JsonResponse({
                'success': True,
                'saved': saved,
                'total': float(total),
                'total_formatted': f"{total:,.0f}",  # 38,000
                'message': f'{saved} payments recorded • UGX {total:,.0f} total',
                'breakdown': breakdown,  # use this to render the list in modal
                'ids': created_ids,  # <-- 4. NEW: [42] or [42,43,44]
                'errors': errors
            })
        
        # Fallback non-JS
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
    
    # Max allowed = current payment + outstanding (so user can increase up to balance)
    max_allowed = loan.outstanding_balance + payment.amount

    if request.method == 'POST':
        book_number = request.POST.get('book_number', '').strip()
        amount_paid = request.POST.get('amount_paid', '').strip()

        # Validation
        if not book_number:
            messages.error(request, "Book number is required")
        elif Repayment.objects.filter(book_number=book_number).exclude(pk=payment.pk).exists():
            messages.error(request, f"Book #{book_number} already used!")
        else:
            try:
                amount_paid = int(amount_paid)
                if amount_paid <= 0:
                    raise ValueError
                if amount_paid > max_allowed:
                    messages.error(request, f"Amount exceeds max allowed UGX {max_allowed}")
                else:
                    repayment.book_number = book_number
                    repayment.amount_paid = amount_paid
                    repayment.save()
                    messages.success(request, f"Payment #{book_number} updated")
                    return redirect('loans:view_payments')  # change to your view name
            except ValueError:
                messages.error(request, "Invalid amount")

    context = {
        'repayment': repayment,
        'loan': loan,
        'max_allowed': max_allowed,
    }
    return render(request, 'loans/edit_payments.html', context)
    
    

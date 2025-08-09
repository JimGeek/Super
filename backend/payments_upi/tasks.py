"""
Celery tasks for UPI payments
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import UPITransaction, UPIMandate, UPIMandateExecution
from .services import UPIPaymentService
import logging

logger = logging.getLogger(__name__)


@shared_task
def check_pending_payments():
    """Check status of pending payments"""
    service = UPIPaymentService()
    
    # Get transactions that are still pending after 5 minutes
    cutoff_time = timezone.now() - timedelta(minutes=5)
    pending_transactions = UPITransaction.objects.filter(
        status__in=['pending', 'processing'],
        initiated_at__lt=cutoff_time
    )
    
    processed_count = 0
    
    for transaction in pending_transactions:
        try:
            provider_service, _ = service.get_provider_service(transaction.provider.code)
            result = provider_service.check_transaction_status(transaction)
            
            if result.get('status') == 'success':
                transaction.status = 'success'
                transaction.upi_txn_id = result.get('upi_txn_id')
                transaction.completed_at = timezone.now()
                transaction.save()
                processed_count += 1
                
            elif result.get('status') == 'failed':
                transaction.status = 'failed'
                transaction.failure_reason = result.get('reason', 'Payment failed')
                transaction.save()
                processed_count += 1
                
        except Exception as e:
            logger.error(f"Failed to check transaction {transaction.txn_ref}: {str(e)}")
    
    # Expire old transactions
    expired_transactions = UPITransaction.objects.filter(
        status__in=['pending', 'processing'],
        expires_at__lt=timezone.now()
    )
    
    expired_count = expired_transactions.update(
        status='expired',
        failure_reason='Transaction expired'
    )
    
    logger.info(f"Processed {processed_count} transactions, expired {expired_count}")
    return {
        'processed': processed_count,
        'expired': expired_count
    }


@shared_task
def process_mandate_charges():
    """Process scheduled mandate charges"""
    service = UPIPaymentService()
    
    # Get mandates that need to be charged
    mandates_to_charge = UPIMandate.objects.filter(
        status='active',
        next_charge_at__lte=timezone.now()
    )
    
    processed_count = 0
    failed_count = 0
    
    for mandate in mandates_to_charge:
        try:
            # Determine charge amount
            if mandate.auto_charge_amount:
                charge_amount = mandate.auto_charge_amount
            else:
                charge_amount = mandate.max_amount
            
            # Create mandate execution
            execution = UPIMandateExecution.objects.create(
                mandate=mandate,
                execution_date=timezone.now().date(),
                amount=charge_amount,
                trigger_type='scheduled'
            )
            
            # Create corresponding transaction
            transaction = UPITransaction.objects.create(
                txn_ref=f"MND_{execution.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}",
                amount=charge_amount,
                payer_vpa=mandate.payer_vpa,
                payee_vpa=mandate.payee_vpa,
                user=mandate.user,
                organization=mandate.organization,
                transaction_type='mandate',
                description=f"Mandate charge - {mandate.description}",
                provider=mandate.provider,
                payment_method='collect',
                expires_at=timezone.now() + timedelta(hours=24)
            )
            
            execution.transaction = transaction
            execution.save()
            
            # Execute mandate
            provider_service, _ = service.get_provider_service(mandate.provider.code)
            result = provider_service.execute_mandate(execution)
            
            if result.get('success'):
                transaction.status = 'processing'
                transaction.provider_response = result
                transaction.save()
                
                # Update mandate next charge date
                if mandate.frequency == 'daily':
                    next_charge = timezone.now() + timedelta(days=1)
                elif mandate.frequency == 'weekly':
                    next_charge = timezone.now() + timedelta(weeks=1)
                elif mandate.frequency == 'monthly':
                    next_charge = timezone.now() + timedelta(days=30)
                elif mandate.frequency == 'quarterly':
                    next_charge = timezone.now() + timedelta(days=90)
                elif mandate.frequency == 'yearly':
                    next_charge = timezone.now() + timedelta(days=365)
                else:  # as_required
                    next_charge = None
                
                mandate.last_charged_at = timezone.now()
                mandate.next_charge_at = next_charge
                mandate.save()
                
                processed_count += 1
                
            else:
                transaction.status = 'failed'
                transaction.failure_reason = result.get('error', 'Mandate execution failed')
                transaction.save()
                
                # Increment retry count
                execution.retry_count += 1
                if execution.retry_count < 3:
                    execution.next_retry_at = timezone.now() + timedelta(hours=1)
                execution.save()
                
                failed_count += 1
                
        except Exception as e:
            logger.error(f"Failed to process mandate {mandate.mandate_ref}: {str(e)}")
            failed_count += 1
    
    logger.info(f"Processed {processed_count} mandates, failed {failed_count}")
    return {
        'processed': processed_count,
        'failed': failed_count
    }


@shared_task
def check_threshold_mandates():
    """Check threshold-based mandates for auto top-up"""
    from settlements.models import LedgerAccount
    
    mandates = UPIMandate.objects.filter(
        status='active',
        purpose='ads_wallet',
        auto_charge_threshold__isnull=False,
        auto_charge_amount__isnull=False
    )
    
    triggered_count = 0
    
    for mandate in mandates:
        try:
            # Get organization's ads wallet balance
            ads_account = LedgerAccount.objects.get(
                type='ads',
                org_id=mandate.organization.id
            )
            
            current_balance = ads_account.get_balance()
            
            if current_balance <= mandate.auto_charge_threshold:
                # Trigger mandate execution
                execution = UPIMandateExecution.objects.create(
                    mandate=mandate,
                    execution_date=timezone.now().date(),
                    amount=mandate.auto_charge_amount,
                    trigger_type='threshold'
                )
                
                # Create transaction (similar to scheduled charge)
                transaction = UPITransaction.objects.create(
                    txn_ref=f"THR_{execution.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}",
                    amount=mandate.auto_charge_amount,
                    payer_vpa=mandate.payer_vpa,
                    payee_vpa=mandate.payee_vpa,
                    user=mandate.user,
                    organization=mandate.organization,
                    transaction_type='mandate',
                    description=f"Auto top-up - {mandate.description}",
                    provider=mandate.provider,
                    payment_method='collect',
                    expires_at=timezone.now() + timedelta(hours=24)
                )
                
                execution.transaction = transaction
                execution.save()
                
                # Execute mandate
                service = UPIPaymentService()
                provider_service, _ = service.get_provider_service(mandate.provider.code)
                result = provider_service.execute_mandate(execution)
                
                if result.get('success'):
                    transaction.status = 'processing'
                    transaction.provider_response = result
                    transaction.save()
                    triggered_count += 1
                
        except Exception as e:
            logger.error(f"Failed to check threshold mandate {mandate.mandate_ref}: {str(e)}")
    
    logger.info(f"Triggered {triggered_count} threshold-based mandates")
    return {'triggered': triggered_count}


@shared_task
def retry_failed_mandate_executions():
    """Retry failed mandate executions"""
    service = UPIPaymentService()
    
    # Get executions that need retry
    executions_to_retry = UPIMandateExecution.objects.filter(
        transaction__status='failed',
        retry_count__lt=3,
        next_retry_at__lte=timezone.now()
    )
    
    retried_count = 0
    
    for execution in executions_to_retry:
        try:
            provider_service, _ = service.get_provider_service(execution.mandate.provider.code)
            result = provider_service.execute_mandate(execution)
            
            if result.get('success'):
                execution.transaction.status = 'processing'
                execution.transaction.provider_response = result
                execution.transaction.save()
                retried_count += 1
            else:
                execution.retry_count += 1
                if execution.retry_count < 3:
                    # Exponential backoff: 1h, 4h, 12h
                    hours = 2 ** execution.retry_count
                    execution.next_retry_at = timezone.now() + timedelta(hours=hours)
                execution.save()
                
        except Exception as e:
            logger.error(f"Failed to retry mandate execution {execution.id}: {str(e)}")
    
    logger.info(f"Retried {retried_count} mandate executions")
    return {'retried': retried_count}


@shared_task
def cleanup_old_webhook_logs():
    """Clean up old webhook logs (keep for 30 days)"""
    from .models import UPIWebhookLog
    
    cutoff_date = timezone.now() - timedelta(days=30)
    deleted_count = UPIWebhookLog.objects.filter(
        received_at__lt=cutoff_date
    ).delete()[0]
    
    logger.info(f"Cleaned up {deleted_count} old webhook logs")
    return {'deleted': deleted_count}
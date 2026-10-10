from web.models.resources import ServiceObservation


def observe(service, success):
    # Diagnostic recording must never turn a successful user operation into failure.
    try:
        ServiceObservation.objects.create(service=service, success=success)
        cutoff = ServiceObservation.objects.order_by('-id').values_list('id', flat=True)[1000:1001]
        if cutoff:
            ServiceObservation.objects.filter(id__lte=cutoff[0]).delete()
    except Exception:
        pass

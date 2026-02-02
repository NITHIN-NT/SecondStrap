from django.shortcuts import redirect,get_object_or_404,render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.views.generic import ListView,DeleteView
from django.utils import timezone
from django.db.models import Sum,Count
from django.db.models.functions import TruncDay
from django.http import JsonResponse
from django.urls import reverse_lazy

from coupon.models import Coupon,CouponUsage
from ..forms import CouponForm

        
@method_decorator([never_cache, staff_member_required(login_url='admin_login')], name="dispatch")
class CouponAdminView(ListView):
    model=Coupon
    context_object_name='coupons'
    template_name = 'coupon/coupons.html'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        now = timezone.now()
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')
        
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        if status == 'Scheduled':
            queryset = queryset.filter(is_active=True,start_date__gt=now)
        elif status == 'Active':
            queryset = queryset.filter(is_active=True)
        elif status == 'Inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['search'] = self.request.GET.get('search')
        context['status'] = self.request.GET.get('status')
        return context
       
@never_cache
@staff_member_required(login_url='admin_login')
def manage_coupon_view(request,id=None):
    
    try:
        coupon = get_object_or_404(Coupon,id=id) if id else None
    except Coupon.DoesNotExist:
        messages.error(request,'Coupon Not found ! Try again')
        return redirect('admin_coupons')
            
    
    if request.method == 'POST':
        form = CouponForm(request.POST,instance=coupon)
        if form.is_valid():
            form.save()
            if id:
                message = 'updated'
            else:
                message = 'created'
            messages.success(request, f'Coupon {message} successfully!')
            return redirect('admin_coupons')  
        else:
            # Form has validation errors
            messages.error(request, 'Please correct the errors below')
    else:
        # GET request
        if coupon :
            form = CouponForm(instance=coupon)
        else:
            form = CouponForm()
            
    
    context = {
        'form': form,
        'coupon':coupon
    }
    return render(request, 'coupon/manage_coupon.html', context)

@method_decorator([never_cache, staff_member_required(login_url='admin_login')], name="dispatch")
class CouponHistoryView(ListView):
    model=CouponUsage
    template_name='coupon/coupon_history.html'
    context_object_name = 'usages'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        total_savings = CouponUsage.objects.aggregate(savings = Sum('discount_amount')) 
        total_coupon_used = CouponUsage.objects.aggregate(count = Count('coupon'))
        chart=(
            CouponUsage.objects.annotate(day=TruncDay('used_at'))
            .values('day')
            .annotate(total=(Count('id')))
            .order_by('day')
        )
        
        context['label'] = [item['day'].strftime('%b %d') for item in chart]
        context['data'] = [int(item['total']) for item in chart]
        
        context['total_savings'] = total_savings['savings'] or 0
        context['total_coupon_used'] = total_coupon_used['count'] or 0
        return context
    
@method_decorator([never_cache, staff_member_required(login_url='admin_login')], name="dispatch")
class CouponDeleteView(DeleteView):
    model=Coupon
    pk_url_kwarg ='pk'
    success_url=reverse_lazy('admin_coupons')
    
    def delete(self,request,*args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        
        return JsonResponse({"message":"Product deleted successfully","redirect_url" : str(self.success_url)})
    
from django.shortcuts import redirect,get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import ListView
from django.db import transaction

from django.db.models import Q
from django.contrib import messages

from accounts.models import CustomUser

@method_decorator([never_cache, staff_member_required(login_url='admin_login')], name="dispatch")
class AdminUserView(LoginRequiredMixin, ListView):
    model = CustomUser
    template_name = "users/home_user.html"
    context_object_name = "Users"
    ordering = ["-date_joined"]
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()

        search_query = self.request.GET.get("search_input", "")
        user_status = self.request.GET.get("userStatus", "")
        if user_status == "active":
            queryset = queryset.filter(is_active=True)
        elif user_status == "blocked":
            queryset = queryset.filter(is_active=False)

        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(phone__icontains=search_query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paginator = context.get("paginator")
        page_obj = context.get("page_obj")

        if paginator and page_obj:
            context["custom_page_range"] = paginator.get_elided_page_range(
                number=page_obj.number, on_each_side=5, on_ends=1
            )
        query_params = self.request.GET.copy()
        if "page" in query_params:
            del query_params["page"]

        context["search_input"] = self.request.GET.get("search_input", "")
        context["user_status"] = self.request.GET.get("userStatus", "")
        return context

@staff_member_required(login_url='admin_login')
@transaction.atomic
@never_cache
def toggle_user_block(request, id):
    if request.method == "POST":
        user = get_object_or_404(CustomUser, id=id)
        user.is_active = not user.is_active
        user.is_verified = not user.is_verified

        user.save()

        status = True if user.is_active else False
        if status:
            messages.success(
                request, f"{user.email} is Unblockd Successfuly", extra_tags="admin"
            )
        else:
            messages.error(
                request, f"{user.email} is Blocked Successfuly", extra_tags="admin"
            )
            return redirect("admin_user")
    else:
        messages.warning(request, "Invalid request method.", extra_tags="admin")
    return redirect("admin_user")

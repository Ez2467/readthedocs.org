from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from vanilla import CreateView, DeleteView, ListView, UpdateView

from readthedocs.core.history import UpdateChangeReasonPostView
from readthedocs.core.mixins import PrivateViewMixin
from readthedocs.organizations.forms import (
    OrganizationSignupForm,
    OrganizationTeamProjectForm,
)
from readthedocs.organizations.models import Organization
from readthedocs.organizations.views.base import (
    OrganizationOwnerView,
    OrganizationTeamMemberView,
    OrganizationTeamView,
    OrganizationView,
)
from readthedocs.sso.models import SSOIntegration
from readthedocsinc.acl.sso.forms import SSOIntegrationForm


# Organization views
class CreateOrganizationSignup(PrivateViewMixin, OrganizationView, CreateView):
    template_name = 'organizations/organization_create.html'
    form_class = OrganizationSignupForm

    def get_form(self, data=None, files=None, **kwargs):
        """Add request user as default billing address email."""
        kwargs['initial'] = {'email': self.request.user.email}
        kwargs['user'] = self.request.user
        return super().get_form(data=data, files=files, **kwargs)

    def get_success_url(self):
        """
        Redirect to Organization's Detail page.

        .. note::

            This method is overriden here from
            ``OrganizationView.get_success_url`` because that method
            redirects to Organization's Edit page.
        """
        return reverse_lazy(
            'organization_detail',
            args=[self.object.slug],
        )


class ListOrganization(PrivateViewMixin, OrganizationView, ListView):
    template_name = 'organizations/organization_list.html'
    admin_only = False

    def get_queryset(self):
        return Organization.objects.for_user(user=self.request.user)


class EditOrganization(
        PrivateViewMixin,
        UpdateChangeReasonPostView,
        OrganizationView,
        UpdateView,
):
    template_name = 'organizations/admin/organization_edit.html'


class DeleteOrganization(
        PrivateViewMixin,
        UpdateChangeReasonPostView,
        OrganizationView,
        DeleteView,
):
    template_name = 'organizations/admin/organization_delete.html'

    def get_success_url(self):
        return reverse_lazy('organization_list')


class OrganizationSSO(PrivateViewMixin, OrganizationView, UpdateView):
    form_class = SSOIntegrationForm
    template_name = 'organizations/admin/sso_edit.html'

    def get_form(self, data=None, files=None, **kwargs):
        self.organization = self.object
        try:
            ssointegration = self.organization.ssointegration
            ssodomain = ssointegration.domains.first()
            initial = {
                'enabled': True,
                'provider': ssointegration.provider,
                'domain': ssodomain.domain if ssodomain else None,
            }
        except SSOIntegration.DoesNotExist:
            ssointegration = None
            initial = {}

        kwargs.update({
            'instance': ssointegration,
            'initial': initial,
        })
        cls = self.get_form_class()
        return cls(self.organization, data, files, **kwargs)

    def get_success_url(self):
        return reverse_lazy(
            'organization_sso',
            args=[self.organization.slug],
        )


# Owners views
class EditOrganizationOwners(PrivateViewMixin, OrganizationOwnerView, ListView):
    template_name = 'organizations/admin/owners_edit.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = self.form_class()
        return context


class AddOrganizationOwner(PrivateViewMixin, OrganizationOwnerView, CreateView):
    template_name = 'organizations/admin/owners_edit.html'
    success_message = _('Owner added')


class DeleteOrganizationOwner(PrivateViewMixin, OrganizationOwnerView, DeleteView):
    template_name = 'organizations/admin/owners_edit.html'
    success_message = _('Owner removed')


# Team views
class AddOrganizationTeam(PrivateViewMixin, OrganizationTeamView, CreateView):
    template_name = 'organizations/team_create.html'
    success_message = _('Team added')


class DeleteOrganizationTeam(
        PrivateViewMixin,
        UpdateChangeReasonPostView,
        OrganizationTeamView,
        DeleteView,
):
    template_name = 'organizations/team_delete.html'
    success_message = _('Team deleted')

    def post(self, request, *args, **kwargs):
        """Hack to show messages on delete."""
        resp = super().post(request, *args, **kwargs)
        messages.success(self.request, self.success_message)
        return resp

    def get_success_url(self):
        return reverse_lazy(
            'organization_team_list',
            args=[self.get_organization().slug],
        )


class EditOrganizationTeam(PrivateViewMixin, OrganizationTeamView, UpdateView):
    template_name = 'organizations/team_edit.html'
    success_message = _('Team updated')


class UpdateOrganizationTeamProject(PrivateViewMixin, OrganizationTeamView, UpdateView):
    form_class = OrganizationTeamProjectForm
    success_message = _('Team projects updated')
    template_name = 'organizations/team_project_edit.html'


class AddOrganizationTeamMember(PrivateViewMixin, OrganizationTeamMemberView, CreateView):
    success_message = _('Member added to team')
    template_name = 'organizations/team_member_create.html'

    def form_valid(self, form):
        form.instance.send_add_notification(self.request)
        return super().form_valid(form)


class DeleteOrganizationTeamMember(PrivateViewMixin, OrganizationTeamMemberView, DeleteView):
    success_message = _('Member removed from team')

    def post(self, request, *args, **kwargs):
        """Hack to show messages on delete."""
        self.object = self.get_object()
        if self.object.invite:
            self.object.invite.delete()
        resp = super().post(request, *args, **kwargs)
        messages.success(self.request, self.success_message)
        return resp

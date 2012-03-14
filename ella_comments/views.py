import operator

from django.contrib import comments
from django.contrib.comments import signals
from django.contrib.comments.views.comments import CommentPostBadRequest
from django.utils.html import escape
from django.template import RequestContext
from django.shortcuts import get_object_or_404, render_to_response
from django.http import HttpResponseRedirect, Http404
from django.db.models import Q
from django.db import transaction
from django.core.paginator import Paginator
from django.conf import settings

from threadedcomments.models import PATH_DIGITS

from ella.core.views import get_templates_from_publishable
from ella.core.custom_urls import resolver

from ella_comments.models import CommentOptionsObject

class CommentView(object):
    def get_template(self, name, context):
        return get_templates_from_publishable(name, context['object'])

class PostComment(CommentView):
    normal_templates = dict(
            form_template = 'comment_form.html',
            preview_template = 'comment_preview.html',
            detail_template = 'comment_detail.html',
        )
    async_templates = dict(
            form_template = 'comment_form_async.html',
            preview_template = 'comment_preview_async.html',
            detail_template = 'comment_detail_async.html',
        )

    def get_default_return_url(self, context):
        return resolver.reverse(context['object'], 'comments-list')

    @transaction.commit_on_success
    def __call__(self, request, context, parent_id=None):
        'Mostly copy-pasted from django.contrib.comments.views.comments'
        templates = self.normal_templates
        if request.is_ajax():
            # async check
            templates = self.async_templates

        opts = CommentOptionsObject.objects.get_for_object(context['object'])
        if opts.blocked:
            raise Http404('Comments are blocked for this object.')
        context['opts'] = opts

        parent = None
        if parent_id:
            parent = get_object_or_404(comments.get_model(), pk=parent_id)

        if request.method != 'POST':
            initial = {}
            if parent:
                if parent.title.startswith('Re:'):
                    initial['title'] = parent.title
                else:
                    initial['title'] = u'Re: %s' % parent.title
            form = comments.get_form()(context['object'], parent=parent_id, initial=initial)
            context.update({
                    'parent': parent,
                    'form': form,
                })
            return render_to_response(
                self.get_template(templates['form_template'], context),
                context,
                RequestContext(request)
            )

        # Fill out some initial data fields from an authenticated user, if present
        data = request.POST.copy()

        if request.user.is_authenticated():
            if not data.get('name', ''):
                data["name"] = request.user.get_full_name() or request.user.username
            if not data.get('email', ''):
                data["email"] = request.user.email

        # construct the form
        form = comments.get_form()(context['object'], data=data, parent=parent_id)

        # Check security information
        if form.security_errors():
            return CommentPostBadRequest(
                "The comment form failed security verification: %s" % \
                    escape(str(form.security_errors())))

        # Do we want to preview the comment?
        preview = "preview" in data

        # Check to see if the POST data overrides the view's next argument.
        next = data.get("next", self.get_default_return_url(context))

        # If there are errors or if we requested a preview show the comment
        if form.errors or preview:
            context.update({
                    "form" : form,
                    'parent': parent,
                    "next": next,
                })
            return render_to_response(
                self.get_template(form.errors and templates['form_template'] or templates['preview_template'], context),
                context,
                RequestContext(request)
            )

        # Otherwise create the comment
        comment = form.get_comment_object()
        comment.ip_address = request.META.get("REMOTE_ADDR", None)
        if request.user.is_authenticated():
            comment.user = request.user

        # Signal that the comment is about to be saved
        responses = signals.comment_will_be_posted.send(
            sender=comment.__class__,
            comment=comment,
            request=request
        )

        for (receiver, response) in responses:
            if response == False:
                return CommentPostBadRequest(
                    "comment_will_be_posted receiver %r killed the comment" % receiver.__name__)

        if opts.premoderated:
            comment.is_public = False

        # Save the comment and signal that it was saved
        comment.save()
        signals.comment_was_posted.send(
            sender=comment.__class__,
            comment=comment,
            request=request
        )

        if next == 'none':
            context.update({
                    "comment" : comment,
                    'parent': parent,
                    "next": next,
                })
            return render_to_response(
                self.get_template(templates['detail_template'], context),
                context,
                RequestContext(request)
            )

        return HttpResponseRedirect(next)

def group_threads(items, prop=lambda x: x.tree_path[:PATH_DIGITS]):
    groups = []
    prev = None
    for i in items:
        if prop(i) != prev:
            prev = prop(i)
            groups.append([])
        groups[-1].append(i)
    return groups

class ListComments(CommentView):
    normal_templates = dict(
            list_template = 'comment_list.html',
        )
    async_templates = dict(
            list_template = 'comment_list_async.html',
        )

    def __call__(self, request, context):
        templates = self.normal_templates
        if request.is_ajax():
            # async check
            templates = self.async_templates

        # basic queryset
        qs = comments.get_model().objects.for_model(context['object']).order_by('tree_path')

        # XXX factor out into a manager
        qs = qs.filter(is_public=True)
        if getattr(settings, 'COMMENTS_HIDE_REMOVED', False):
            qs = qs.filter(is_removed=False)

        # only individual branches requested
        if 'ids' in request.GET:
            ids = request.GET.getlist('ids')
            # branch is everything whose tree_path begins with the same prefix
            qs = qs.filter(reduce(
                        operator.or_,
                        map(lambda x: Q(tree_path__startswith=x.zfill(PATH_DIGITS)), ids)
                ))

        # pagination and other get params TODO: use Form for this
        if 'p' in request.GET and request.GET['p'].isdigit():
            page_no = int(request.GET['p'])
        else:
            page_no = 1
        paginate_by = getattr(settings, 'COMMENTS_PAGINATE_BY', 50)
        if 'pby' in request.GET and request.GET['pby'].isdigit():
            if 0 < int(request.GET['pby']) <= 100:
                paginate_by = int(request.GET['pby'])
        reverse = False
        if 'reverse' in request.GET and request.GET['reverse'].isdigit():
            reverse = bool(int(request.GET['reverse']))

        if getattr(settings, 'COMMENTS_GROUP_THREADS', False):
            items = group_threads(qs)
        elif getattr(settings, 'COMMENTS_FLAT', False):
            items = list(qs.order_by('-submit_date'))
        else:
            items = list(qs)
        if reverse:
            items = list(reversed(items))

        paginator = Paginator(items, paginate_by)

        if page_no > paginator.num_pages or page_no < 1:
            raise Http404()

        page = paginator.page(page_no)
        context.update({
            'comment_list': page.object_list,
            'page': page,
            'is_paginated': paginator.num_pages > 1,
            'results_per_page': paginate_by,
        })

        return render_to_response(
            self.get_template(templates['list_template'], context),
            context,
            RequestContext(request)
        )

post_comment = PostComment()
list_comments = ListComments()


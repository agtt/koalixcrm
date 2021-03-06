# -*- coding: utf-8 -*-

from django.db import models
from django.utils.translation import ugettext as _
from django.contrib import admin
from koalixcrm.crm.reporting.employeeassignmenttotask import EmployeeAssignmentToTask, InlineEmployeeAssignmentToTask
from koalixcrm.crm.reporting.generictasklink import InlineGenericTaskLink
from koalixcrm.crm.reporting.work import InlineWork
from koalixcrm.crm.documents.pdfexport import PDFExport
from datetime import *
from rest_framework import serializers
import koalixcrm


class Task(models.Model):
    title = models.CharField(verbose_name=_("Title"), max_length=100, blank=True, null=True)
    planned_start_date = models.DateField(verbose_name=_("Planned Start Date"), blank=True, null=True)
    planned_end_date = models.DateField(verbose_name=_("Planned End Date"), blank=True, null=True)
    project = models.ForeignKey("Project", verbose_name=_('Project'), blank=False, null=False)
    description = models.TextField(verbose_name=_("Description"), blank=True, null=True)
    status = models.ForeignKey("TaskStatus", verbose_name=_('Task Status'), blank=True, null=True)
    last_status_change = models.DateField(verbose_name=_("Last Status Change"), blank=True, null=False)

    def planned_duration(self):
        if (not self.planned_start_date) or (not self.planned_end_date):
            return 0
        elif self.planned_start_date > self.planned_end_date:
            return 0
        else:
            return self.planned_end_date-self.planned_start_date

    def planned_effort(self):
        assignments_to_this_task = EmployeeAssignmentToTask.objects.filter(task=self.id)
        sum_effort = 0
        for assignment_to_this_task in assignments_to_this_task:
            sum_effort += assignment_to_this_task.planned_effort
        return sum_effort

    def effective_duration(self):
        if self.status:
            if self.status.is_done:
                if self.planned_start_date > self.last_status_change:
                    return 0
                else:
                    return self.last_status_change - self.planned_start_date
        return "n/a"

    def serialize_to_xml(self):
        objects = [self, ]
        main_xml = PDFExport.write_xml(objects)
        for work in koalixcrm.crm.reporting.work.Work.objects.filter(task=self.id):
            work_xml = work.serialize_to_xml()
            main_xml = PDFExport.merge_xml(main_xml, work_xml)
        main_xml = PDFExport.append_element_to_pattern(main_xml,
                                                       "object/[@model='crm.task']",
                                                       "Effective_Effort",
                                                       self.effective_effort())
        main_xml = PDFExport.append_element_to_pattern(main_xml,
                                                       "object/[@model='crm.task']",
                                                       "Planned_Effort",
                                                       self.planned_effort())
        main_xml = PDFExport.append_element_to_pattern(main_xml,
                                                       "object/[@model='crm.task']",
                                                       "Effective_Duration",
                                                       self.effective_duration())
        main_xml = PDFExport.append_element_to_pattern(main_xml,
                                                       "object/[@model='crm.task']",
                                                       "Planned_Duration",
                                                       self.planned_duration())
        return main_xml

    def effective_effort(self):
        work_objects = koalixcrm.crm.reporting.work.Work.objects.filter(task=self.id)
        sum_effort = 0
        for work_object in work_objects:
            if (not work_object.start_time) or (not work_object.stop_time):
                sum_effort = 0
            elif work_object.start_time > work_object.stop_time:
                sum_effort += 0
            else:
                sum_effort += work_object.effort()
        sum_effort_in_hours = sum_effort / 3600
        return sum_effort_in_hours

    def get_title(self):
        if self.title:
            return self.title
        else:
            return "n/a"

    def __str__(self):
        return str(self.id) + " " + self.get_title()

    class Meta:
        app_label = "crm"
        verbose_name = _('Task')
        verbose_name_plural = _('Tasks')


class OptionTask(admin.ModelAdmin):
    list_display = ('id',
                    'title',
                    'planned_start_date',
                    'planned_end_date',
                    'project',
                    'status',
                    'last_status_change',
                    'planned_duration',
                    'planned_effort',
                    'effective_duration',
                    'effective_effort')
    list_display_links = ('id',)
    list_filter = ('project',)
    ordering = ('-id',)

    fieldsets = (
        (_('Work'), {
            'fields': ('title',
                       'planned_start_date',
                       'planned_end_date',
                       'project',
                       'description',
                       'status')
        }),
    )
    save_as = True
    inlines = [InlineEmployeeAssignmentToTask,
               InlineGenericTaskLink,
               InlineWork]

    def save_model(self, request, obj, form, change):
        obj.last_status_change = date.today().__str__()
        obj.save()


class InlineTasks(admin.TabularInline):
    model = Task
    readonly_fields = ('planned_duration',
                       'planned_effort',
                       'effective_duration',
                       'effective_effort')
    fieldsets = (
        (_('Task'), {
            'fields': ('id',
                       'title',
                       'planned_start_date',
                       'planned_end_date',
                       'status',
                       'last_status_change',
                       'planned_duration',
                       'planned_effort',
                       'effective_duration',
                       'effective_effort')
        }),
    )
    extra = 0

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class TaskJSONSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Task
        fields = ('id',
                  'title',
                  'planned_end_date',
                  'planned_start_date',
                  'project',
                  'description',
                  'status')

from rest_framework import serializers
from django.utils import timezone
from .models import Subject, Chapter, Topic


class SubjectSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.name', read_only=True)

    class Meta:
        model = Subject
        fields = '__all__'


class TopicSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Topic
        fields = ['id', 'title', 'is_completed', 'completed_date']


class ChapterSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    completion_percentage = serializers.FloatField(read_only=True)
    topics = TopicSerializer(many=True, required=False)

    class Meta:
        model = Chapter
        fields = [
            'id',
            'subject',
            'subject_name',
            'chapter_number',
            'chapter_title',
            'description',
            'status',
            'completion_percentage',
            'target_date',
            'completed_date',
            'remarks',
            'reminder_enabled',
            'reminder_days_before',
            'notify_students_on_completion',
            'topics',
        ]

    def create(self, validated_data):
        topics_data = validated_data.pop('topics', [])
        chapter = Chapter.objects.create(**validated_data)
        for t_data in topics_data:
            is_comp = t_data.get('is_completed', False)
            comp_date = t_data.get('completed_date')
            if is_comp and not comp_date:
                comp_date = timezone.now().date()
            Topic.objects.create(
                chapter=chapter,
                title=t_data.get('title', ''),
                is_completed=is_comp,
                completed_date=comp_date
            )
        return chapter

    def update(self, instance, validated_data):
        topics_data = validated_data.pop('topics', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if instance.status == 'completed' and not instance.completed_date:
            instance.completed_date = timezone.now().date()

        instance.save()

        if topics_data is not None:
            existing_topics = {t.id: t for t in instance.topics.all()}
            for t_data in topics_data:
                topic_id = t_data.get('id')
                is_comp = t_data.get('is_completed', False)
                comp_date = t_data.get('completed_date')
                if is_comp and not comp_date:
                    comp_date = timezone.now().date()

                if topic_id and topic_id in existing_topics:
                    t_obj = existing_topics[topic_id]
                    if 'title' in t_data:
                        t_obj.title = t_data['title']
                    t_obj.is_completed = is_comp
                    t_obj.completed_date = comp_date if is_comp else None
                    t_obj.save()
                else:
                    Topic.objects.create(
                        chapter=instance,
                        title=t_data.get('title', ''),
                        is_completed=is_comp,
                        completed_date=comp_date
                    )

        return instance


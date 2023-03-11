import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.forms import PostForm
from posts.models import Group, Post, User

SHIFT_POST = 3
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.auth = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self) -> None:
        self.auth_client = Client()
        self.auth_client.force_login(self.auth)
        self.post = Post.objects.create(
            author=self.auth,
            text='Тестовый пост kjljf;sakdj;fskaj;flkjasd;klfjs;l',
            group=self.group,
            image=self.uploaded
        )
        cache.clear()

    def post_or_page_obj(self, response, is_it_true=False):
        if is_it_true:
            post = response.context['post']
        else:
            post = response.context['page_obj'][0]
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(
            post.author, self.post.author
        )
        self.assertEqual(post.group, self.group)
        self.assertEqual(post.pub_date, self.post.pub_date)
        self.assertEqual(post.image, self.post.image)

    def test_home_page_shows_correct_context(self):
        """Тест: глав. страница показывает правильный контекст"""
        response = self.auth_client.get(reverse('posts:index'))
        self.post_or_page_obj(response)

    def test_group_list_shows_correct_context(self):
        """Текст: страница группы показывает правильный контекст"""
        response = self.auth_client.get(
            reverse('posts:group_posts', args=(self.group.slug,))
        )
        self.post_or_page_obj(response)
        self.assertEqual(response.context['group'].title, self.group.title)
        self.assertEqual(response.context['group'].slug, self.group.slug)
        self.assertEqual(
            response.context['group'].description, self.group.description)

    def test_profile_page_shows_correct_context(self):
        """Тест: станица профайла показывает правильный контекст"""
        response = self.auth_client.get(
            reverse('posts:profile', args=(self.auth,))
        )
        self.post_or_page_obj(response)
        self.assertEqual(
            response.context['author'], self.auth
        )

    def test_post_detail_page_shows_correct_context(self):
        """Тест: страница поста показывает правильный контекст"""
        response = self.auth_client.get(
            reverse('posts:post_detail', args=(self.post.pk,))
        )
        self.post_or_page_obj(response, True)

    def test_post_in_right_group(self):
        """Тест: пост закрепился за правильной группой """
        group2 = Group.objects.create(
            title='Тестовая группа New',
            slug='New-slug',
            description='Тестовое описание New',
        )
        response = self.auth_client.get(
            reverse('posts:group_posts', args=(group2.slug,))
        )
        self.assertEqual(len(response.context['page_obj']), 0)
        self.assertEqual(self.post.group, self.group)
        response = self.auth_client.get(
            reverse('posts:group_posts', args=(self.group.slug,))
        )
        self.assertEqual(len(response.context['page_obj']), 1)

    def test_create_and_edit_shows_correct_context(self):
        """Тест: При создании и редактировании поста правильный контекст"""
        namespace_name: tuple = (
            ('posts:post_create', None, ),
            ('posts:post_edit', (self.post.pk,), ),
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for namespace, name in namespace_name:
            with self.subTest(namespace=namespace, name=name):
                response = self.auth_client.get(
                    reverse(namespace, args=(name))
                )
                self.assertIn('form', response.context)
                form = response.context.get('form')
                self.assertIsInstance(form, PostForm)
                for value, expected in form_fields.items():
                    with self.subTest(value=value):
                        form_field = response.context.get(
                            'form'
                        ).fields.get(value)
                        self.assertIsInstance(form_field, expected)

    def test_cache(self):
        """ Проверка кэша (не в карманах) на начальной странице"""
        response = self.auth_client.get(reverse('posts:index'))
        self.post.delete()
        response_after = self.auth_client.get(reverse('posts:index'))
        self.assertEqual(response.content, response_after.content)
        cache.clear()
        response = self.auth_client.get(reverse('posts:index'))
        self.assertNotEqual(response.content, response_after.content)
        # print((post.object_list))


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.auth = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

        batch_size = settings.LIMITS_IN_PAGE + SHIFT_POST
        posts: list = []
        for _ in range(batch_size):
            posts.append(Post(
                author=cls.auth,
                text='Тестовый пост kjljf;sakdj;fskaj;flkjasd;klfjs;l',
                group=cls.group,
            ))
        Post.objects.bulk_create(posts)

    def setUp(self) -> None:
        self.auth_client = Client()
        self.auth_client.force_login(self.auth)

    def test_index_correct_posts_numbers_on_page(self):
        """Тестирование пажинатора"""
        names_args: tuple = (
            ('posts:index', None, ),
            ('posts:group_posts', (self.group.slug,), ),
            ('posts:profile', (self.auth,), ),
        )
        pages: tuple = (
            ('?page=1', settings.LIMITS_IN_PAGE),
            ('?page=2', SHIFT_POST),
        )

        for name, args in names_args:
            with self.subTest(name=name):
                for page, page_quantity in pages:
                    with self.subTest(page=page, page_quantity=page_quantity):
                        response = self.auth_client.get(
                            reverse(name, args=args) + page
                        )
                        posts_on_pages = (
                            len(response.context['page_obj'].object_list)
                        )
                        self.assertEqual(posts_on_pages, page_quantity)

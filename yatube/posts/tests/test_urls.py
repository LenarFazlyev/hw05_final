from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Comment, Group, Post, User


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост kjljf;sakdj;fskaj;flkjasd;klfjs;l',
        )
        cls.auth = User.objects.create_user(username='auth')
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.author,
            text='Testing comment made by author'
        )

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.auth_client = Client()
        self.auth_client.force_login(self.auth)
        self.urls: tuple = (
            ('posts:index', None, '/'),
            ('posts:group_posts',
             (self.group.slug,),
             f'/group/{self.group.slug}/'
             ),
            ('posts:profile', (self.auth,), f'/profile/{self.auth}/'),
            ('posts:post_detail',
             (self.post.pk,),
             f'/posts/{self.post.pk}/'
             ),
            ('posts:post_create', None, '/create/'),
            ('posts:post_edit',
             (self.post.pk,),
             f'/posts/{self.post.pk}/edit/'
             ),
            ('posts:add_comment',
             (self.post.pk,),
             f'/posts/{self.post.pk}/comment/'
             ),
            ('posts:follow_index',
             None,
             '/follow/'
             ),
            ('posts:profile_follow',
             (self.author,),
             f'/profile/{self.author}/follow/'
             ),
            ('posts:profile_unfollow',
             (self.author,),
             f'/profile/{self.author}/unfollow/'
             ),
        )

    def test_pages_use_correct_templates(self):
        """Тест: Страница использует правильные шаблоны"""
        templates: tuple = (
            ('posts:index', None, 'posts/index.html'),
            ('posts:group_posts', (self.group.slug,), 'posts/group_list.html'),
            ('posts:profile', (self.auth,), 'posts/profile.html'),
            ('posts:post_detail', (self.post.pk,), 'posts/post_detail.html'),
            ('posts:post_create', None, 'posts/create_post.html'),
            ('posts:post_edit', (self.post.pk,), 'posts/create_post.html'),
            ('posts:follow_index', None, 'posts/follow.html'),
        )
        for namespace, args, template in templates:
            with self.subTest(template=template):
                response = self.author_client.get(
                    reverse(namespace, args=args)
                )
                self.assertTemplateUsed(response, template)

    def test_post_404(self):
        """Тест: Код 404 для не допустимой страницы"""
        response = self.client.get('/posts/2/')
        self.assertEqual(response.status_code, 404)

    def test_pages_uses_correct_urls(self):
        """Тест: Страница использует правильные пути"""
        for namespace, args, url in self.urls:
            with self.subTest(url=url):
                response = reverse(namespace, args=args)
                self.assertEqual(response, url)

    def test_urls_for_author(self):
        """Тестирование урлов автора"""
        for namespace, args, _ in self.urls:
            with self.subTest(url=_):
                response = self.author_client.get(
                    reverse(namespace, args=args),
                )
                if namespace == 'posts:add_comment':
                    reverse_name = reverse(
                        'posts:post_detail', args=(self.post.pk,)
                    )
                    self.assertRedirects(
                        response, (f'{reverse_name}')
                    )
                elif namespace == 'posts:profile_follow':
                    reverse_name = reverse(
                        'posts:profile', args=(self.author,)
                    )
                    self.assertRedirects(
                        response, (f'{reverse_name}')
                    )
                elif namespace == 'posts:profile_unfollow':
                    self.assertEqual(
                        response.status_code,
                        HTTPStatus.NOT_FOUND
                    )
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_for_auth(self):
        """Тестирование урлов авторизованного пользователя"""
        for namespace, args, _ in self.urls:
            with self.subTest(namespace=namespace):
                response = self.auth_client.get(reverse(namespace, args=args))
                if (namespace == 'posts:post_edit'
                        or namespace == 'posts:add_comment'):
                    url_from_reverse = reverse(
                        'posts:post_detail', args=(self.post.pk,)
                    )
                    self.assertRedirects(response, url_from_reverse)
                elif (namespace == 'posts:profile_follow'
                        or namespace == 'posts:profile_unfollow'):
                    url_from_reverse = reverse(
                        'posts:profile', args=(self.author,)
                    )
                    self.assertRedirects(response, url_from_reverse)
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_for_not_auth(self):
        """Тестирование урлов неавторизированного пользователя"""
        edit_or_create: list = [
            'posts:post_create',
            'posts:post_edit',
            'posts:add_comment',
            'posts:follow_index',
            'posts:profile_follow',
            'posts:profile_unfollow',
        ]

        for namespace, args, _ in self.urls:
            with self.subTest(namespace=namespace):
                response = self.client.get(
                    reverse(namespace, args=args),
                )
                if namespace in edit_or_create:
                    reverse_login = reverse('users:login')
                    reverse_name = reverse(namespace, args=args)
                    self.assertRedirects(
                        response, (f'{reverse_login}?next={reverse_name}')
                    )
                else:
                    self.assertEqual(response.status_code, HTTPStatus.OK)

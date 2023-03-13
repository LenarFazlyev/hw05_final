import shutil
import tempfile

from http import HTTPStatus

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache

from ..forms import PostForm
from ..models import Follow, Group, Post, User, Comment

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateAndEditFormsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author')

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.group_new = Group.objects.create(
            title='Тестовая группа два',
            slug='test-slugtwo',
            description='Тестовое описание два',
        )
        cls.form = PostForm()
        # small_gif = (
        #     b'\x47\x49\x46\x38\x39\x61\x02\x00'
        #     b'\x01\x00\x80\x00\x00\x00\x00\x00'
        #     b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
        #     b'\x00\x00\x00\x2C\x00\x00\x00\x00'
        #     b'\x02\x00\x01\x00\x00\x02\x02\x0C'
        #     b'\x0A\x00\x3B'
        # )
        # cls.uploaded = SimpleUploadedFile(
        #     name='small.gif',
        #     content=small_gif,
        #     content_type='image/gif'
        # )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост kjljf;sakdj;fskaj;flkjasd;klfjs;l',
            group=cls.group,
            # image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.author_client = Client()
        self.author_client.force_login(self.author)
        # self.post = Post.objects.create(
        #     author=self.author,
        #     text='Тестовый пост нумер ван',
        #     group=self.group,
        #     image=self.uploaded
        # )

    def test_create_post_authorized(self):
        """
        Тест возможность создания поста авторизированным клиентом
        2023-03-10 добавил в форм-дата картинку.
        """
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded1 = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'group': self.group.id,
            'text': 'Тестовый текст нумер ту',
            'image': uploaded1  # добавил картинку.
        }
        # Убедился что пост один в базе, до создания еще одного.
        Post.objects.all().delete()
        self.assertEqual(Post.objects.count(), 0)
        response = self.author_client.post(
            reverse('posts:post_create'),
            data=form_data
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:profile',
                args=(self.author.username,),
            ),
        )
        self.assertEqual(Post.objects.count(), 1)
        post = Post.objects.first()
        self.assertEqual(
            post.author, self.author
        )  # автор
        self.assertEqual(
            post.group.pk, form_data['group']
        )  # группа
        self.assertEqual(
            post.text, form_data['text']
        )  # текст
        self.assertEqual(post.image, f"posts/{form_data['image']}")

    def test_create_post_not_authorized(self):
        """Тестирование невозможности создания поста гостем"""
        post_count = Post.objects.count()
        form_data = {
            'group': self.group.id,
            'text': 'Тестовый текст нумер трии',
        }
        # Убедился что пост один в базе, до создания еще одного.
        self.assertEqual(Post.objects.count(), 1)
        response = self.client.post(
            reverse('posts:post_create'), data=form_data
        )
        # Убедился что количество постов не изменилось
        self.assertEqual(Post.objects.count(), post_count)
        # Убедился что не авторизованный получил редирект
        self.assertEqual(response.status_code, 302)

    def test_edit_post_authorized(self):
        """Тестирование редактирования поста пользователем"""
        posts_count = Post.objects.count()
        form_data = {
            'group': self.group_new.id,
            'text': 'Отредактированный пост',
        }

        response = self.author_client.post(
            reverse(
                'posts:post_edit',
                args=(self.post.id,),
            ),
            data=form_data,
            follow=True,
        )
        modified_post = Post.objects.first()
        # проверка что кол-во постов не изменилось
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(modified_post.text, form_data['text'])
        self.assertEqual(modified_post.author, self.post.author)
        self.assertEqual(modified_post.group.pk, form_data['group'])
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                args=(self.post.id,),
            ),
        )
        response = self.client.get(
            reverse('posts:group_posts', args=(self.group.slug,))
        )
        # Сделать запрос на старую группу, проверить что пришел код 200
        self.assertEqual(response.status_code, HTTPStatus.OK)
        page = response.context['page_obj']
        # Проверил что постов в группе 0.
        self.assertEqual(len(page.object_list), 0)
        # Сравнил id постов до и после
        self.assertEqual(modified_post.pk, self.post.pk)


class CommentTestCase(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username='author')
        # self.author_client = Client()
        # self.author_client.force_login(self.author)
        self.post = Post.objects.create(
            author=self.author,
            text='Тестовый пост нумер ван',
        )
        self.auth = User.objects.create_user(username='auth')
        self.auth_client = Client()
        self.auth_client.force_login(self.auth)

    def test_comment_post_auth(self):  # нужно доработать
        """
        проверка comment добавляется у авторизованного пользователя
        и отображается на странице поста
        """
        Comment.objects.all().delete()  # удаляю все комментарии
        self.assertEqual(Comment.objects.count(), 0)
        form_data = {'text': 'New commentdddd'}
        response = self.auth_client.post(
            reverse(
                'posts:add_comment',
                args=(self.post.id,),
            ),
            data=form_data,
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                args=(self.post.id,),
            ),
        )
        self.assertEqual(Comment.objects.count(), 1)
        comment = Comment.objects.first()
        self.assertEqual(comment.text, form_data['text'])
        self.assertEqual(comment.post, self.post)
        self.assertEqual(comment.author, self.auth)

    def test_comment_post_not_auth(self):  # нужно доработать
        """ проверка коммент может только добавлять авторизованный"""
        Comment.objects.all().delete()  # удаляю все комментарии
        self.assertEqual(Comment.objects.count(), 0)
        form_data = {'text': 'New commentdddd'}
        response = self.client.post(
            reverse(
                'posts:add_comment',
                args=(self.post.id,),
            ),
            data=form_data,
        )
        self.assertEqual(Comment.objects.count(), 0)
        self.assertEqual(
            response.status_code, 302
        )  # как вариант заменить на HTTPStatus.FOUND


class FollowTestCase(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.auth = User.objects.create_user(username='auth')
        cls.auth2 = User.objects.create_user(username='auth2')
        cls.author = User.objects.create_user(username='author')
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый пост kjljf;sakdj;fskaj;flkjasd;klfjs;l',
        )

    def setUp(self) -> None:
        self.auth_client = Client()
        self.auth_client.force_login(self.auth)
        self.auth_client2 = Client()
        self.auth_client2.force_login(self.auth2)

    def test_auth_can_follow(self):
        """Авторизованный пользователь может подписываться на автора"""
        initial_follows = Follow.objects.count()
        self.auth_client.get(
            reverse(
                'posts:profile_follow',
                args=(self.author,),
            )
        )
        after_follows = Follow.objects.count()
        self.assertEqual(after_follows, initial_follows + 1)
        # self.assertTrue(Follow.objects.filter(
        #     user=self.auth,
        #     author=self.author
        # ).exists())
        followers = Follow.objects.last()
        self.assertEqual(followers.author, self.author)
        self.assertEqual(followers.user, self.auth)

    def test_auth_can_unfollow(self):
        """Отписка авторизованного пользователя"""
        Follow.objects.create(
            user=self.auth,
            author=self.author
        )
        initial_follows = Follow.objects.count()
        self.auth_client.get(
            reverse(
                'posts:profile_unfollow',
                args=(self.author,),
            )
        )
        after_unfollows = Follow.objects.count()
        self.assertEqual(after_unfollows, initial_follows - 1)

    def test_new_post_showsup_only_follower(self):
        """Пост показывается только у подписчиков"""
        response = self.auth_client.get(
            reverse('posts:follow_index')
        )
        self.assertEqual(len(response.context['page_obj']), 0)
        Follow.objects.create(
            user=self.auth,
            author=self.author
        )
        response = self.auth_client.get(
            reverse('posts:follow_index')
        )
        self.assertEqual(len(response.context['page_obj']), 1)

    def test_cannot_follow_yourself(self):
        follower_count = Follow.objects.count()
        self.auth_client.get(
            reverse('posts:profile_follow', args=(self.auth,))
        )
        follower_count_after = Follow.objects.count()
        self.assertEqual(follower_count, follower_count_after)

    def test_second_try_to_follow(self):
        follower_count = Follow.objects.count()
        self.auth_client.get(
            reverse('posts:profile_follow', args=(self.author,))
        )
        follower_count_first = Follow.objects.count()
        self.assertEqual(follower_count, follower_count_first - 1)
        self.auth_client.get(
            reverse('posts:profile_follow', args=(self.author,))
        )
        follower_count_second = Follow.objects.count()
        self.assertEqual(follower_count_second, follower_count_first)

import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient

from recipe.serializers import RecipeSerializer, RecipeDetailSerializer

RECIPES_URL = reverse('recipe:recipe-list')

def image_upload_url(recipe_id):
    """Return url for Recipe image upload"""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def detail_url(recipe_id):
    """return recipe detail for given ID"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def sample_tag(user, name='Main course'):
    """Create and return a sample tag"""
    return Tag.objects.create(user=user, name=name)

def sample_ingredient(user, name='Cinnamon'):
    """create and return a sample tag"""
    return Ingredient.objects.create(user=user, name=name)


def sample_recipe(user, **params):
    """create and return a sample recipe"""
    defaults = {
        'title': 'Sample Recipe',
        'time_minutes': 10,
        'price': 5.00
    }
    defaults.update(params)

    return Recipe.objects.create(user=user, **defaults)


class PublicRecipeApiTests(TestCase):
    """Test unauthenticated recipe API access"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that Authentication is required"""
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
    
class PrivateRecipeApiTests(TestCase):
    """Test authenticated recipe API access"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'test@doit.com',
            'testpass'
        )
        self.client.force_authenticate(self.user)
    
    def test_retrieve_recipes(self):
        """test retrieeing a list of recipes"""

        sample_recipe(user=self.user)
        sample_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
    
    def test_recipes_limited_to_user(self):
        """Test retrieving recipes for user"""
        user2 = get_user_model().objects.create_user(
            'other@doit.com',
            'pass123'
        )
        sample_recipe(user=user2)
        sample_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data, serializer.data)
    
    def test_view_recipe_detail(self):
        """test viewing a recipe detail"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        recipe.ingredients.add(sample_ingredient(user=self.user))

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)
    
    def test_create_basic_recipe(self):
        """test creating recipe"""
        payload = {
            'title': 'Chocalate Cheesecake',
            'time_minutes': 30,
            'price': 5.00
        }
        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))
    
    def test_create_recipe_with_tags(self):
        """Test creating a recipe with Tags"""
        tag1 = sample_tag(user=self.user, name='Vegan')
        tag2 = sample_tag(user=self.user, name='Dessert')

        payload = {
            'title': 'Avocado lime cheesecake',
            'tags': [tag1.id, tag2.id],
            'time_minutes': 60,
            'price': 20.00
        }
        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data['id'])
        tags = recipe.tags.all()
        self.assertEqual(tags.count(), 2)
        self.assertIn(tag1, tags)
        self.assertIn(tag2, tags)

    def test_create_recipe_with_ingredients(self):
        """Test creating a recipe with Ingredients"""
        ing1 = sample_ingredient(user=self.user, name='Prawns')
        ing2 = sample_ingredient(user=self.user, name='Ginger')

        payload = {
            'title': 'Thai red prawn curry',
            'ingredients': [ing1.id, ing2.id],
            'time_minutes': 60,
            'price': 20.00
        }
        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipe = Recipe.objects.get(id=res.data['id'])
        ingredients = recipe.ingredients.all()
        self.assertEqual(ingredients.count(), 2)
        self.assertIn(ing1, ingredients)
        self.assertIn(ing2, ingredients)
    
    def test_partial_update_recipe(self):
        """Test updating a recipe with patch[Pirtial changes]"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        new_tag = sample_tag(user=self.user, name='Curry')

        payload = {'title': 'Chicken Tikka', 'tags': [new_tag.id]}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        tags = recipe.tags.all()
        self.assertEqual(len(tags), 1)
        self.assertIn(new_tag, tags)
    
    def test_full_update_recipe(self):
        """Test updating a recipe with put"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        payload = {
            'title' : 'Spaghetti carbonara',
            'time_minutes' : 25,
            'price' : 5.00 
        }
        url = detail_url(recipe.id)
        self.client.put(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.time_minutes, payload['time_minutes'])
        self.assertEqual(recipe.price, payload['price'])
        tags = recipe.tags.all()
        self.assertEqual(len(tags), 0)

class RecipeImageUploadTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@doit.com', 
            'testpass'
        )
        self.client.force_authenticate(self.user)
        self.recipe = sample_recipe(user=self.user)
    
    def tearDown(self):
        self.recipe.image.delete()
    
    def test_upload_image_to_recipe(self):
        """Test uploading image to a recipe"""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as ntf:
            img = Image.new('RGB', (10, 10))
            img.save(ntf, format='JPEG')
            ntf.seek(0)
            res = self.client.post(url, {'image': ntf}, format='multipart')
        
        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))
    
    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.recipe.id)
        res = self.client.post(url, {'image': 'notimage'}, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_filter_recipe_by_tags(self):
        """Test for recipes filtered by tags"""
        recipe_1 = sample_recipe(user=self.user, title='Thai vegetable curry')
        recipe_2 = sample_recipe(user=self.user, title='Aubergine with tahini')
        tag1 = sample_tag(user=self.user, name='Vegan')
        tag2 = sample_tag(user=self.user, name='Vegetarian')
        recipe_1.tags.add(tag1)
        recipe_2.tags.add(tag2)
        recipe_3 = sample_recipe(user=self.user, title='Fish and chips')

        res = self.client.get(
            RECIPES_URL,
            {'tags': f'{tag1.id},{tag2.id}'}
        )

        serializer1 = RecipeSerializer(recipe_1)
        serializer2 = RecipeSerializer(recipe_2)
        serializer3 = RecipeSerializer(recipe_3)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_recipe_by_ingredients(self):
        """Test for recipes filtered by ingredients"""
        recipe_1 = sample_recipe(user=self.user, title='Thai vegetable curry')
        recipe_2 = sample_recipe(user=self.user, title='Aubergine with tahini')
        ing1 = sample_ingredient(user=self.user, name='Onion')
        ing2 = sample_ingredient(user=self.user, name='Garlic')
        recipe_1.ingredients.add(ing1)
        recipe_2.ingredients.add(ing1)
        recipe_3 = sample_recipe(user=self.user, title='Fish and chips')

        res = self.client.get(
            RECIPES_URL,
            {'ingredients': f'{ing1.id},{ing2.id}'}
        )

        serializer1 = RecipeSerializer(recipe_1)
        serializer2 = RecipeSerializer(recipe_2)
        serializer3 = RecipeSerializer(recipe_3)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)
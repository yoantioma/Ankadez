from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError('L’adresse e-mail est obligatoire.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault('is_staff', False)
        extra.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('role', User.Role.ADMIN)
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    """Utilisateur connecté par e-mail. Il appartient à une organisation (PME, fonds, structure…)."""

    class Role(models.TextChoices):
        PME = 'pme', 'PME'
        INVESTISSEUR = 'investisseur', 'Investisseur'
        PARTENAIRE = 'partenaire', 'Structure d’accompagnement'
        INSTITUTION = 'institution', 'Institution'
        ADMIN = 'admin', 'Administrateur'

    username = None
    email = models.EmailField('adresse e-mail', unique=True)
    role = models.CharField('rôle', max_length=20, choices=Role.choices, default=Role.PME)
    telephone = models.CharField('téléphone', max_length=40, blank=True)
    organisation = models.ForeignKey('annuaire.Organisation', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='membres', verbose_name='organisation')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
        verbose_name = 'utilisateur'

    def __str__(self):
        return self.get_full_name() or self.email

    @property
    def est_pme(self):
        return self.role == self.Role.PME

    @property
    def est_investisseur(self):
        return self.role == self.Role.INVESTISSEUR

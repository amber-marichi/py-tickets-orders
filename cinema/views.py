from datetime import datetime
from typing import Type
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count, F, QuerySet

from cinema.models import (
    Genre,
    Actor,
    CinemaHall,
    Movie,
    MovieSession,
    Order,
)

from cinema.serializers import (
    GenreSerializer,
    ActorSerializer,
    CinemaHallSerializer,
    MovieSerializer,
    MovieSessionSerializer,
    MovieSessionListSerializer,
    MovieDetailSerializer,
    MovieSessionDetailSerializer,
    MovieListSerializer,
    OrderListSerializer,
    OrderSerializer,
)


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer


class ActorViewSet(viewsets.ModelViewSet):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer


class CinemaHallViewSet(viewsets.ModelViewSet):
    queryset = CinemaHall.objects.all()
    serializer_class = CinemaHallSerializer


class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.prefetch_related("genres", "actors")
    serializer_class = MovieSerializer

    def get_serializer_class(self) -> Type[serializer_class]:
        if self.action == "list":
            return MovieListSerializer

        if self.action == "retrieve":
            return MovieDetailSerializer

        return MovieSerializer

    def get_queryset(self) -> QuerySet:
        queryset = self.queryset

        if self.action == "list":
            title = self.request.query_params.get("title")
            if title:
                queryset = queryset.filter(title__icontains=title)
            actors = self.request.query_params.get("actors")
            if actors:
                actors_ids = str_ids_to_int(actors)
                queryset = queryset.filter(actors__id__in=actors_ids)
            genres = self.request.query_params.get("genres")
            if genres:
                genres_ids = str_ids_to_int(genres)
                queryset = queryset.filter(genres__id__in=genres_ids)

            queryset = queryset.distinct()

        return queryset


class MovieSessionViewSet(viewsets.ModelViewSet):
    queryset = MovieSession.objects.select_related("movie", "cinema_hall")
    serializer_class = MovieSessionSerializer

    def get_serializer_class(self) -> Type[serializer_class]:
        if self.action == "list":
            return MovieSessionListSerializer

        if self.action == "retrieve":
            return MovieSessionDetailSerializer

        return MovieSessionSerializer

    def get_queryset(self) -> QuerySet:
        queryset = self.queryset

        if self.action == "list":
            queryset = (
                queryset.annotate(
                    tickets_available=(
                        F("cinema_hall__seats_in_row")
                        * F("cinema_hall__rows")
                        - Count("tickets")
                    )
                )
            )
            movie = self.request.query_params.get("movie")
            if movie:
                movie_ids = str_ids_to_int(movie)
                queryset = queryset.filter(movie_id__in=movie_ids)
            date_str = self.request.query_params.get("date")
            if date_str:
                date_obj = str_to_date(date_str)
                queryset = queryset.filter(show_time__contains=date_obj)

            queryset = queryset.distinct()

        return queryset


class OrderPagination(PageNumberPagination):
    page_size = 5
    page_query_param = "page_size"
    max_page_size = 10


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.prefetch_related(
        "tickets__movie_session__cinema_hall",
        "tickets__movie_session__movie"
    )
    pagination_class = OrderPagination

    def get_queryset(self) -> QuerySet:
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer) -> None:
        serializer.save(user=self.request.user)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer
        return OrderSerializer


def str_ids_to_int(queries: str) -> list[int]:
    return [int(str_id) for str_id in queries.split(",")]


def str_to_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d").date()

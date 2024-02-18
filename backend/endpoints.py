"""
List of  available remote endpoints

Each endpoint accepts item-id \n
Some accept also a name. For more details visit docs.

Detailed docs: https://pokeapi.co/docs/v2
"""

from enum import Enum


class EndpointName(str, Enum):
    """List of valid endpoints"""

    # Berries group start
    berry = "berry"
    berry_firmness = "berry-firmness"
    berry_flavor = "berry-flavor"
    # Berries group end

    # Contests group start
    contest_type = "contest-type"
    contest_effect = "contest-effect"
    super_contest_effect = "super-contest-effect"
    # Contests group end

    # Encounters group start
    encounter_method = "encounter-method"
    encounter_condition = "encounter-condition"
    encounter_condition_value = "encounter-condition-value"
    # Encounters group end

    # Evolution group start
    evolution_chain = "evolution-chain"
    evolution_trigger = "evolution-trigger"
    # Evolution group end

    # Games group start
    generation = "generation"
    pokedex = "pokedex"
    version = "version"
    version_group = "version-group"
    # Games group end

    # Items group start
    item = "item"
    item_attribute = "item-attribute"
    item_category = "item-category"
    item_fling_effect = "item-fling-effect"
    item_pocket = "item-pocket"
    # Items group end

    # Locations group start
    location = "location"
    location_area = "location-area"
    pal_park_area = "pal-park-area"
    region = "region"
    # Locations group start

    # Machines group start
    machine = "machine"
    # Machines group end

    # Moves group start
    move = "move"
    move_ailment = "move-ailment"
    move_category = "move-category"
    move_damage_class = "move-damage-class"
    move_learn_method = "move-learn-method"
    move_target = "move-target"
    # Moves group end

    # Pokémon group start
    ability = "ability"
    characteristic = "characteristic"
    egg_group = "egg-group"
    gender = "gender"
    growth_rate = "growth-rate"
    nature = "nature"
    pokeathlon_stat = "pokeathlon-stat"
    pokemon = "pokemon"
    pokemon_color = "pokemon-color"
    pokemon_form = "pokemon-form"
    pokemon_habitat = "pokemon-habitat"
    pokemon_shape = "pokemon-shape"
    pokemon_species = "pokemon-species"
    stat = "stat"
    type = "type"
    # Pokémon group end

    # Utility group start
    language = "language"
    # Utility group end

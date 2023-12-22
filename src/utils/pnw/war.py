from __future__ import annotations
import math
import re
from typing import Union
from warnings import WarningMessage
import numpy as np

import aiohttp
from ...types import TradePrices, Nation, WarPolicyDetails, WarTypeDetails, WarTypeEnum, WarPolicyEnum, AttackType, MilitaryUnit, MilitaryUnitEnum, AttackSuccess, AttackerEnum, StatsEnum, WarAttackerFilter, WarActiveFilter
from .. import execute_query, weird_division
from . import SOLDIERS_PER_BARRACKS, TANKS_PER_FACTORY, AIRCRAFT_PER_HANGAR, SHIPS_PER_DRYDOCK, BARRACKS_PER_CITY, FACTORY_PER_CITY, HANGAR_PER_CITY, DRYDOCK_PER_CITY, RESOURCES, infra_cost


def beige_loot_value(loot_string: str, prices: TradePrices) -> int:
    loot_string = loot_string[loot_string.index(
        '$'):loot_string.index('Food.')]
    loot_string = re.sub(r"[^0-9-]+", "", loot_string.replace(", ", "-"))
    n = 0
    loot = {}
    for sub in loot_string.split("-"):
        loot[RESOURCES[n]] = int(sub)
        n += 1
    nation_loot = 0
    for rs in RESOURCES:
        amount = loot[rs]
        price = prices[rs]
        nation_loot += amount * price
    return nation_loot


def barracks_mmr(barracks: int, cities: int, decimal: int = 1) -> float:
    return round(barracks / cities, decimal)


def factory_mmr(factories: int, cities: int, decimal: int = 1) -> float:
    return round(factories / cities, decimal)


def hangar_mmr(hangars: int, cities: int, decimal: int = 1) -> float:
    return round(hangars / cities, decimal)


def drydock_mmr(drydocks: int, cities: int, decimal: int = 1) -> float:
    return round(drydocks / cities, decimal)


def population_soldiers_limit(population: int) -> int:
    return math.floor(population/6.67)


def population_tanks_limit(population: int) -> int:
    return math.floor(population/66.67)


def population_aircraft_limit(population: int) -> int:
    return math.floor(population/1000)


def population_ships_limit(population: int) -> int:
    return math.floor(population/10000)


def max_soldiers(barracks: int, population: int) -> int:
    return math.floor(min(SOLDIERS_PER_BARRACKS * barracks, population_soldiers_limit(population)))


def max_tanks(factories: int, population: int) -> int:
    return math.floor(min(TANKS_PER_FACTORY * factories, population_tanks_limit(population)))


def max_aircraft(hangars: int, population: int) -> int:
    return math.floor(min(AIRCRAFT_PER_HANGAR * hangars, population_aircraft_limit(population)))


def max_ships(drydocks: int, population: int) -> int:
    return math.floor(min(SHIPS_PER_DRYDOCK * drydocks, population_ships_limit(population)))


def max_spies(central_intelligence_agency: bool) -> int:
    return 60 if central_intelligence_agency else 50


def soldiers_daily(barracks: int, population: int, propaganda_bureau: int) -> int:
    return round(max_soldiers(barracks, population)/3) * (1.1 if propaganda_bureau else 1)


def tanks_daily(factories: int, population: int, propaganda_bureau: int) -> int:
    return round(max_tanks(factories, population)/5) * (1.1 if propaganda_bureau else 1)


def aircraft_daily(hangars: int, population: int, propaganda_bureau: int) -> int:
    return round(max_aircraft(hangars, population)/5) * (1.1 if propaganda_bureau else 1)


def ships_daily(drydocks: int, population: int, propaganda_bureau: int) -> int:
    return round(max_ships(drydocks, population)/5) * (1.1 if propaganda_bureau else 1)


def spies_daily(central_intelligence_agency: bool, spy_satellite: bool) -> int:
    return 1 + int(central_intelligence_agency) + int(spy_satellite)


def days_to_max_soldiers(soldiers: int, barracks: int, population: int, propaganda_bureau: int) -> int:
    return math.ceil(weird_division(max_soldiers(barracks, population) - soldiers, soldiers_daily(barracks, population, propaganda_bureau)))


def days_to_max_tanks(tanks: int, factories: int, population: int, propaganda_bureau: int) -> int:
    return math.ceil(weird_division(max_tanks(factories, population) - tanks, tanks_daily(factories, population, propaganda_bureau)))


def days_to_max_aircraft(aircraft: int, hangars: int, population: int, propaganda_bureau: int) -> int:
    return math.ceil(weird_division(max_aircraft(hangars, population) - aircraft, aircraft_daily(hangars, population, propaganda_bureau)))


def days_to_max_ships(ships: int, drydocks: int, population: int, propaganda_bureau: int) -> int:
    return math.ceil(weird_division(max_ships(drydocks, population) - ships, ships_daily(drydocks, population, propaganda_bureau)))


def days_to_max_spies(spies: int, central_intelligence_agency: bool, spy_satellite: bool) -> int:
    return math.ceil(weird_division(max_spies(central_intelligence_agency) - spies, spies_daily(central_intelligence_agency, spy_satellite)))


def soldiers_absolute_militarization(soldiers: int, cities: int) -> float:
    return soldiers / (cities * BARRACKS_PER_CITY * SOLDIERS_PER_BARRACKS)


def soldiers_relative_militarization(soldiers: int, barracks: int) -> float:
    return soldiers / (barracks * SOLDIERS_PER_BARRACKS)


def tanks_absolute_militarization(tanks: int, cities: int) -> float:
    return tanks / (cities * FACTORY_PER_CITY * TANKS_PER_FACTORY)


def tanks_relative_militarization(tanks: int, factories: int) -> float:
    return tanks / (factories * TANKS_PER_FACTORY)


def aircraft_absolute_militarization(aircraft: int, cities: int) -> float:
    return aircraft / (cities * HANGAR_PER_CITY * AIRCRAFT_PER_HANGAR)


def aircraft_relative_militarization(aircraft: int, hangars: int) -> float:
    return aircraft / (hangars * AIRCRAFT_PER_HANGAR)


def ships_absolute_militarization(ships: int, cities: int) -> float:
    return ships / (cities * DRYDOCK_PER_CITY * SHIPS_PER_DRYDOCK)


def ships_relative_militarization(ships: int, drydocks: int) -> float:
    return ships / (drydocks * SHIPS_PER_DRYDOCK)


def total_absolute_militarization(soldiers: int, tanks: int, aircraft: int, ships: int, cities: int) -> float:
    return (soldiers_absolute_militarization(soldiers, cities) + tanks_absolute_militarization(tanks, cities) + aircraft_absolute_militarization(aircraft, cities) + ships_absolute_militarization(ships, cities)) / 4


def total_relative_militarization(soldiers: int, barracks: int, tanks: int, factories: int, aircraft: int, hangars: int, ships: int, drydocks: int) -> float:
    return (soldiers_relative_militarization(soldiers, barracks) + tanks_relative_militarization(tanks, factories) + aircraft_relative_militarization(aircraft, hangars) + ships_relative_militarization(ships, drydocks)) / 4


@WarningMessage.deprecated("This function is deprecated. Use the spy field in `Nation` instead.")
async def spy_calc(nation: Nation) -> int:
    """
    Calculates the amount of spies a nation has.
    """
    async with aiohttp.ClientSession() as session:
        if nation.war_policy == WarPolicyEnum.ARCANE:
            percent = 57.5
        elif nation.war_policy == WarPolicyEnum.TACTICIAN:
            percent = 42.5
        else:
            percent = 50
        upper_lim = 60
        lower_lim = 0
        while True:
            spycount = math.floor((upper_lim + lower_lim)/2)
            async with session.get(f"https://politicsandwar.com/war/espionage_get_odds.php?id1=341326&id2={nation['id']}&id3=0&id4=1&id5={spycount}") as probability:
                probability = await probability.text()
            if "Greater than 50%" in probability:
                upper_lim = spycount
            else:
                lower_lim = spycount
            if upper_lim - 1 == lower_lim:
                break
        enemyspy = round((((100*int(spycount))/(percent-25))-2)/3)
        if enemyspy > 60:
            enemyspy = 60
        elif enemyspy > 50 and not nation._central_intelligence_agency:
            enemyspy = 50
        elif enemyspy < 2:
            enemyspy = 0
    return enemyspy


class BattleCalc:
    async def __init__(self, attacker: Nation, defender: Nation) -> None:
        self.attacker = attacker
        self.defender = defender
        
        self.war = None
        for war in await attacker.get_wars(WarAttackerFilter.ALL, WarActiveFilter.ACTIVE):
            if war.defender == defender:
                self.war = war
                break

        self.attacker_using_munitions = True
        self.defender_using_munitions = True

        self.attacker_air_superiority = self.war.air_superiority == self.attacker.id if self.war else False
        self.defender_air_superiority = self.war.air_superiority == self.defender.id if self.war else False

        self.attacker_fortified = self.war.att_fortify if self.war else False
        self.defender_fortified = self.war.def_fortify if self.war else False

        self.attacker_air_value = self.attacker.aircraft * MilitaryUnit(MilitaryUnitEnum.AIRCRAFT).army_value
        self.defender_air_value = self.defender.aircraft * MilitaryUnit(MilitaryUnitEnum.AIRCRAFT).army_value

        self.attacker_naval_value = self.attacker.ships * MilitaryUnit(MilitaryUnitEnum.SHIP).army_value
        self.defender_naval_value = self.defender.ships * MilitaryUnit(MilitaryUnitEnum.SHIP).army_value

        self.attacker_casualties_aircraft_value = weird_division((self.attacker_air_value + self.defender_air_value) , (self.attacker_air_value ** (3/4) + self.defender_air_value ** (3/4))) * self.attacker_air_value ** (3/4)
        self.defender_casualties_aircraft_value = weird_division((self.attacker_air_value + self.defender_air_value) , (self.attacker_air_value ** (3/4) + self.defender_air_value ** (3/4))) * self.defender_air_value ** (3/4)

        self.attacker_casualties_ships_value = weird_division((self.attacker_naval_value + self.defender_naval_value) , (self.attacker_naval_value ** (3/4) + self.defender_naval_value ** (3/4))) * self.attacker_naval_value ** (3/4)
        self.defender_casualties_ships_value = weird_division((self.attacker_naval_value + self.defender_naval_value) , (self.attacker_naval_value ** (3/4) + self.defender_naval_value ** (3/4))) * self.defender_naval_value ** (3/4)

    @property
    def attacker_ground_army_value(self) -> float:
        return self.attacker_soldiers_value + self.attacker_tanks_value
    
    @property
    def attacker_soldiers_value(self) -> float:
        return self.attacker.soldiers * MilitaryUnit(MilitaryUnitEnum.SOLDIER, using_munitions = self.attacker_using_munitions).army_value

    @property
    def attacker_tanks_value(self) -> float:
        return self.attacker.tanks * MilitaryUnit(MilitaryUnitEnum.TANK, enemy_air_superiority = self.defender_air_superiority).army_value

    @property
    def defender_ground_army_value(self) -> float:
        return self.defender_soldiers_value + self.defender_tanks_value + self.defender_population_value
    
    @property
    def defender_soldiers_value(self) -> float:
        return self.defender.soldiers * MilitaryUnit(MilitaryUnitEnum.SOLDIER, using_munitions = self.defender_using_munitions).army_value
    
    @property
    def defender_tanks_value(self) -> float:
        return self.defender.tanks * MilitaryUnit(MilitaryUnitEnum.TANK, enemy_air_superiority = self.attacker_air_superiority).army_value
    
    @property
    def defender_population_value(self) -> float:
        return self.defender.population / 400 * MilitaryUnit(MilitaryUnitEnum.SOLDIER, using_munitions = self.defender_using_munitions).army_value
    
    @property
    def ground_winrate(self) -> float:
        """
        Calculates the ground winrate of the attacker.
        """
        return universal_winrate(self.attacker_ground_army_value, self.defender_ground_army_value)
    
    @property
    def air_winrate(self) -> float:
        """
        Calculates the air winrate of the attacker.
        """
        return universal_winrate(self.attacker.aircraft, self.defender.aircraft)
    
    @property
    def naval_winrate(self) -> float:
        """
        Calculates the naval winrate of the attacker.
        """
        return universal_winrate(self.attacker.ships, self.defender.ships)
    
    @property
    def total_winrate(self) -> float:
        """
        Calculates the total winrate of the attacker.
        """
        return (self.ground_winrate() + self.air_winrate() + self.naval_winrate()) / 3
    
    def attack_result_type_odds(self, attack_type: AttackType, result_type: AttackSuccess) -> float:
        """
        Calculates the odds of a specific attack result.
        """
        if attack_type == AttackType.GROUND:
            winrate_func = self.ground_winrate
        elif attack_type in [AttackType.AIRVAIR, AttackType.AIRVINFRA, AttackType.AIRVMONEY, AttackType.AIRVSHIPS, AttackType.AIRVSOLDIERS, AttackType.AIRVTANKS]:
            winrate_func = self.air_winrate
        elif attack_type == AttackType.NAVAL:
            winrate_func = self.naval_winrate
        else:
            raise Exception("Invalid attack type.")

        if result_type == AttackSuccess.IMMENSE_TRIUMPH:
            return winrate_func ** 3
        elif result_type == AttackSuccess.MODERATE_SUCCESS:
            return (winrate_func ** 2) * (1 - winrate_func)
        elif result_type == AttackSuccess.PYRRHIC_VICTORY:
            return winrate_func * ((1 - winrate_func) ** 2)
        elif result_type == AttackSuccess.UTTER_FAILURE:
            return (1 - winrate_func) ** 3
    
    def attack_result_all_types_odds(self, attack_type: AttackType) -> dict[AttackSuccess, float]:
        """
        Calculates the odds of all attack results.
        """
        return {
            result_type: self.attack_result_type_odds(attack_type, result_type)
            for result_type in AttackSuccess
        }

    @property
    def attacker_casualties_soldiers_value(self):    
        return weird_division((self.attacker_soldiers_value + self.defender_soldiers_value) , (self.attacker_soldiers_value ** (3/4) + self.defender_soldiers_value ** (3/4))) * self.attacker_soldiers_value ** (3/4)

    @property
    def attacker_casualties_tanks_value(self):    
        return weird_division((self.attacker_tanks_value + self.defender_tanks_value) , (self.attacker_tanks_value ** (3/4) + self.defender_tanks_value ** (3/4))) * self.attacker_tanks_value ** (3/4)

    @property
    def defender_casualties_soldiers_value(self):    
        return weird_division((self.attacker_soldiers_value + self.defender_soldiers_value) , (self.attacker_soldiers_value ** (3/4) + self.defender_soldiers_value ** (3/4))) * self.defender_soldiers_value ** (3/4)

    @property
    def defender_casualties_tanks_value(self):    
        return weird_division((self.attacker_tanks_value + self.defender_tanks_value) , (self.attacker_tanks_value ** (3/4) + self.defender_tanks_value ** (3/4))) * self.defender_tanks_value ** (3/4)

    # TODO how does population come into play?
    # defender_casualties_population_value = (self.defender.population / 400) ** (3/4)

    def __stat_type_to_normal_casualties_modifier(self, stat_type: StatsEnum) -> float:
        """
        Converts a stat type to a normal casualties modifier. Average is 0.7 and difference is 0.3.
        """
        if stat_type == StatsEnum.AVERAGE:
            return 0.7
        elif stat_type == StatsEnum.DIFFERENCE:
            return 0.3
        else:
            raise ValueError("Invalid stat type")

    def __defender_fortified(self, func):
        """
        The attacker's casualties. Is 1.25 if the defender is fortified.
        """
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs) * 1 if not self.defender_fortified else 1.25
        return wrapper

    @__defender_fortified
    def ground_attack_attacker_soldiers_casualties(self, stat_type: StatsEnum) -> float:
        """
        Calculates the amount of soldiers the attacker will lose in a ground attack.
        """
        random_modifier = self.__stat_type_to_normal_casualties_modifier(stat_type)
        return (self.defender_casualties_soldiers_value * 0.0084 + self.defender_casualties_tanks_value * 0.0092) * random_modifier
    
    @__defender_fortified
    def ground_attack_attacker_tanks_casualties(self, stat_type: StatsEnum) -> float:
        """
        Calculates the amount of tanks the attacker will lose in a ground attack.
        """
        random_modifier = self.__stat_type_to_normal_casualties_modifier(stat_type)
        return (
            self.defender_casualties_soldiers_value * (0.0004060606 * self.ground_winrate + 0.00043225806 * (1 - self.ground_winrate))
            + self.defender_casualties_tanks_value * (0.00066666666 * self.ground_winrate + 0.00070967741 * (1 - self.ground_winrate))
            ) * random_modifier

    def ground_attack_defender_soldiers_casualties(self, stat_type: StatsEnum) ->  float:
        """
        Calculates the amount of soldiers the defender will lose in a ground attack.
        """
        random_modifier = self.__stat_type_to_normal_casualties_modifier(stat_type)
        return (self.attacker_casualties_soldiers_value * 0.0084 + self.attacker_casualties_tanks_value * 0.0092) * random_modifier
    
    def ground_attack_defender_tanks_casualties(self, stat_type: StatsEnum) -> float:
        """
        Calculates the amount of tanks the defender will lose in a ground attack.
        """
        random_modifier = self.__stat_type_to_normal_casualties_modifier(stat_type)
        return (
            self.attacker_casualties_soldiers_value * (0.0004060606 * (1 - self.ground_winrate) + 0.00043225806 * self.ground_winrate)
            + self.attacker_casualties_tanks_value * (0.00066666666 * (1 - self.ground_winrate) + 0.00070967741 * self.ground_winrate)
            ) * random_modifier
    
    def ground_attack_defender_aircraft_casualties(self, stat_type: StatsEnum) -> float:
        """
        Calculates the amount of aircraft the defender will lose in a ground attack.
        """
        # TODO what are the casualty ratios?
        if stat_type == StatsEnum.AVERAGE:
            return self.attacker.tanks * 0.005 * self.ground_winrate ** 3
        elif stat_type == StatsEnum.DIFFERENCE:
            return self.attacker.tanks * 0.005 * (1 - self.ground_winrate) ** 3
        else:
            raise ValueError("Invalid stat type")
    
    @__defender_fortified
    def air_v_air_attacker_aircraft_casualties(self, stat_type: StatsEnum) -> float:
        """
        Calculates the amount of aircraft the attacker will lose in an air v air attack.
        """
        random_modifier = self.__stat_type_to_normal_casualties_modifier(stat_type)
        return (self.defender_casualties_aircraft_value * 0.01) * random_modifier
    
    def air_v_air_defender_aircraft_casualties(self, stat_type: StatsEnum) -> float:
        """
        Calculates the amount of aircraft the defender will lose in an air v air attack.
        """
        random_modifier = self.__stat_type_to_normal_casualties_modifier(stat_type)
        return (self.attacker_casualties_aircraft_value * 0.018337) * random_modifier
    
    @__defender_fortified
    def air_v_other_attacker_aircraft_casualties(self, stat_type: StatsEnum) -> float:
        """
        Calculates the amount of aircraft the attacker will lose in an air v other attack.
        """
        random_modifier = self.__stat_type_to_normal_casualties_modifier(stat_type)
        return (self.defender_casualties_aircraft_value * 0.015385) * random_modifier
    
    def air_v_other_defender_aircraft_casualties(self, stat_type: StatsEnum) -> float:
        """
        Calculates the amount of aircraft the defender will lose in an air v other attack.
        """
        random_modifier = self.__stat_type_to_normal_casualties_modifier(stat_type)
        return (self.attacker_casualties_aircraft_value * 0.009091) * random_modifier
    
    def __airstrike_unit_kill_rate(self, func) -> function:
        def wrapper(*args, **kwargs):
            rate = -0.4624 * self.air_winrate**2 + 1.06256 * self.air_winrate + 0.3999            
            if rate < 0.4:
                rate = 0.4
            return func(*args, **kwargs) * rate
        return wrapper
    
    def __stat_type_to_airstrike_casualties_modifier(self, stat_type: StatsEnum) -> float:
        if stat_type == StatsEnum.AVERAGE:
            return 0.95
        elif stat_type == StatsEnum.DIFFERENCE:
            return 0.1
        else:
            raise ValueError("Invalid stat type")
    
    def air_v_infra_defender_infra_lost(self) -> float:
        # TODO
        return 0

    def air_v_money_defender_money_lost(self) -> float:
        # TODO
        return 0
    
    @__airstrike_unit_kill_rate
    def air_v_ships_defender_ships_casualties(self, stat_type: StatsEnum) -> float:
        """
        Calculates the amount of ships the defender will lose in an air v ships attack.
        """
        # TODO is it correct to use the random_modifier here?
        random_modifier = self.__stat_type_to_airstrike_casualties_modifier(stat_type)
        return round(max(min(self.defender.ships, self.defender.ships * 0.75 + 4, (self.attacker.aircraft - self.defender.aircraft * 0.5) * 0.0285 * random_modifier), 0))
    
    @__airstrike_unit_kill_rate
    def air_v_soldiers_defender_soldiers_casualties(self, stat_type: StatsEnum) -> float:
        """
        Calculates the amount of soldiers the defender will lose in an air v soldiers attack.
        """
        # TODO is it correct to use the random_modifier here?
        random_modifier = self.__stat_type_to_airstrike_casualties_modifier(stat_type)
        return round(max(min(self.defender.soldiers, self.defender.soldiers * 0.75 + 1000, (self.attacker.aircraft - self.defender.aircraft * 0.5) * 35 * random_modifier), 0))
    
    @__airstrike_unit_kill_rate
    def air_v_tanks_defender_tanks_casualties(self, stat_type: StatsEnum) -> float:
        """
        Calculates the amount of tanks the defender will lose in an air v tanks attack.
        """
        # TODO is it correct to use the random_modifier here?
        random_modifier = self.__stat_type_to_airstrike_casualties_modifier(stat_type)
        return round(max(min(self.defender.tanks, self.defender.tanks * 0.75 + 10, (self.attacker.aircraft - self.defender.aircraft * 0.5) * 1.25 * random_modifier), 0))
    
    def naval_attack_attacker_ships_casualties(self, stat_type: StatsEnum) -> float:
        """
        Calculates the amount of ships the attacker will lose in a naval attack.
        """
        random_modifier = self.__stat_type_to_normal_casualties_modifier(stat_type)
        return (self.defender_casualties_ships_value * 0.01375) * random_modifier    
    
    def naval_attack_defender_ships_casualties(self, stat_type: StatsEnum) -> float:
        """
        Calculates the amount of ships the defender will lose in a naval attack.
        """
        random_modifier = self.__stat_type_to_normal_casualties_modifier(stat_type)
        return (self.attacker_casualties_ships_value * 0.01375) * random_modifier
    
    def ground_attack_loot(self, stat_type: StatsEnum) -> float:
        """
        Calculates the amount of loot the attacker will get in a ground attack.
        """
        random_modifier = self.__stat_type_to_normal_casualties_modifier(stat_type)
        return (
            (self.attacker.soldiers * MilitaryUnit(MilitaryUnitEnum.SOLDIER).loot_stolen
                + self.attacker.tanks * MilitaryUnit(MilitaryUnitEnum.TANK).loot_stolen)
            * ((self.ground_winrate ** 3) * 3
                + (self.ground_winrate ** 2) * (1 - self.ground_winrate) * 2
                + self.ground_winrate * (1 - self.ground_winrate) ** 2)   
            * random_modifier
            * self.war._war_type_details.attacker_loot if self.war else WarTypeDetails(WarTypeEnum.ORDINARY).attacker_loot
            * self.attacker.war_policy_details.loot_stolen
            * self.defender.war_policy_details.loot_lost
            * 1.05 if self.attacker._advanced_pirate_economy else 1
            * 1.05 if self.attacker._pirate_economy else 1
            # TODO * blitzkrieg
        )
    
    def __infrastructure_destroyed(self, func, only_war: bool = False):
        """
        Modifies the amount of infrastructure destroyed according to policies and war types.
        """
        def wrapper(*args, **kwargs):
            if self.war:
                if self.war.attacker == self.attacker:
                    war_modifier = self.war._war_type_details.attacker_infra_destroyed
                elif self.war.defender == self.attacker:
                    war_modifier = self.war._war_type_details.defender_infra_destroyed
                else:
                    raise ValueError("Invalid attacker")
            else:
                war_modifier = WarTypeDetails(WarTypeEnum.ORDINARY).attacker_infra_destroyed
            
            if only_war:
                return func(*args, **kwargs) * war_modifier
            else:
                return (
                    func(*args, **kwargs)
                    * war_modifier
                    * self.attacker.war_policy_details.infrastructure_damage_dealt
                    * self.defender.war_policy_details.infrastructure_damage_received)
        return wrapper
    
    @__infrastructure_destroyed
    async def ground_attack_infrastructure_destroyed(self, stat_type: StatsEnum) -> float:
        random_modifier = self.__stat_type_to_airstrike_casualties_modifier(stat_type)
        return (
            max(
                min(((self.attacker.soldiers - self.defender.soldiers * 0.5) * 0.000606061
                        + (self.attacker.tanks - (self.defender.tanks * 0.5)) * 0.01)
                    * random_modifier
                    * self.ground_winrate ** 3 
                    , (await self.defender.highest_infra_city).infrastructure * 0.2 + 25)
                , 0))
    
    @__infrastructure_destroyed
    async def air_v_infra_infrastructure_destroyed(self, stat_type: StatsEnum) -> float:
        random_modifier = self.__stat_type_to_airstrike_casualties_modifier(stat_type)
        return (
            max(
                min((self.attacker.aircraft - self.defender.aircraft * 0.5) * 0.35353535
                    * random_modifier
                    * self.air_winrate ** 3
                    , (await self.defender.highest_infra_city).infrastructure * 0.5 + 100)
                , 0))
    
    # @__infrastructure_destroyed
    async def air_v_other_infrastructure_destroyed(self, stat_type: StatsEnum) -> float:
        return self.air_v_infra_infrastructure_destroyed(stat_type) / 3
    
    @__infrastructure_destroyed
    async def naval_attack_infrastructure_destroyed(self, stat_type: StatsEnum) -> float:
        random_modifier = self.__stat_type_to_airstrike_casualties_modifier(stat_type)
        return (
            max(
                min((self.attacker.ships - self.defender.ships * 0.5) * 2.625
                    * random_modifier
                    * self.naval_winrate ** 3
                    , (await self.defender.highest_infra_city).infrastructure * 0.5 + 25)
                , 0))
    
    @__infrastructure_destroyed(only_war = True)
    async def missile_strike_infrastructure_destroyed(self, stat_type: StatsEnum) -> float:
        city = await self.defender.highest_infra_city
        
        avg = (300 + max(350, city.infrastructure * 100 / city.land * 3)) / 2
        diff = max(350, city.infrastructure * 100 / city.land * 3) - avg

        if stat_type == StatsEnum.AVERAGE:
            x = avg
        elif stat_type == StatsEnum.DIFFERENCE:
            x = diff
        else:
            raise ValueError("Invalid stat type")
        
        return (max(min(x, city.infrastructure * 0.8 + 150), 0))

    @__infrastructure_destroyed(only_war = True)
    async def nuclear_attack_infrastructure_destroyed(self, stat_type: StatsEnum) -> float:
        city = await self.defender.highest_infra_city

        avg = (1700 + max(2000, city.infrastructure * 100 / city.land * 13.5)) / 2
        diff = max(2000, city.infrastructure * 100 / city.land * 13.5) - avg

        if stat_type == StatsEnum.AVERAGE:
            x = avg
        elif stat_type == StatsEnum.DIFFERENCE:
            x = diff
        else:
            raise ValueError("Invalid stat type")
        
        return (max(min(x, city.infrastructure * 0.8 + 150), 0))
    
    async def __infrastructure_destroyed_value(self, func) -> float:
        """
        Calculates the value of infrastructure destroyed.
        """
        async def wrapper(*args, **kwargs):
            starting = (await self.defender.highest_infra_city).infrastructure
            ending = starting - await func(*args, **kwargs)
            return infra_cost(starting, ending, self.defender)
        return wrapper
    
    @__infrastructure_destroyed_value
    async def ground_attack_infrastructure_destroyed_value(self, stat_type: StatsEnum) -> float:
        """
        Calculates the value of infrastructure destroyed in a ground attack.
        """
        return await self.ground_attack_infrastructure_destroyed(stat_type)
    
    @__infrastructure_destroyed_value
    async def air_v_infra_infrastructure_destroyed_value(self, stat_type: StatsEnum) -> float:
        """
        Calculates the value of infrastructure destroyed in an air v infra attack.
        """
        return await self.air_v_infra_infrastructure_destroyed(stat_type)
    
    @__infrastructure_destroyed_value
    async def air_v_other_infrastructure_destroyed_value(self, stat_type: StatsEnum) -> float:
        """
        Calculates the value of infrastructure destroyed in an air v other (than infra) attack.
        """
        return await self.air_v_other_infrastructure_destroyed(stat_type)
    
    @__infrastructure_destroyed_value
    async def naval_attack_infrastructure_destroyed_value(self, stat_type: StatsEnum) -> float:
        """
        Calculates the value of infrastructure destroyed in a naval attack.
        """
        return await self.naval_attack_infrastructure_destroyed(stat_type)
    
    @__infrastructure_destroyed_value
    async def missile_strike_infrastructure_destroyed_value(self, stat_type: StatsEnum) -> float:
        """
        Calculates the value of infrastructure destroyed in a missile strike.
        """
        return await self.missile_strike_infrastructure_destroyed(stat_type)
    
    @__infrastructure_destroyed_value
    async def nuclear_attack_infrastructure_destroyed_value(self, stat_type: StatsEnum) -> float:
        """
        Calculates the value of infrastructure destroyed in a nuclear attack.
        """
        return await self.nuclear_attack_infrastructure_destroyed(stat_type)
    
    def __recovered_by_military_salvage(self, attacker_used: float, defender_used: float, winrate: float) -> float:
        """
        Calculates the amount of resources recovered by military salvage.
        """
        return (attacker_used + defender_used) * (int(self.attacker._military_salvage) * (winrate ** 3) * 0.05)

    def ground_attack_defender_aluminum_used(self, stat_type: StatsEnum) -> float:
        """
        Calculates the amount of aluminum used by the defender in a ground attack.
        """
        return self.ground_attack_defender_aircraft_casualties(stat_type) * MilitaryUnit(MilitaryUnitEnum.AIRCRAFT).aluminum_cost
    
    def ground_attack_attacker_aluminum_used(self, stat_type: StatsEnum) -> float:
        """
        Calculates the amount of aluminum used by the attacker in a ground attack.
        """
        return self.__recovered_by_military_salvage(0, self.ground_attack_defender_aircraft_casualties(stat_type), self.ground_winrate)
    
    


            

    



    


    

def universal_winrate(attacker_army_value: float, defender_army_value: float):
    """
    Calculates the winrate of the attacker.
    """
    # TODO: redo this function

    attacker_army_value **= (3/4)
    defender_army_value **= (3/4)

    if attacker_army_value == 0 and defender_army_value == 0:
        return 0
    elif defender_army_value == 0:
        return 1
    x = attacker_army_value / defender_army_value

    # should be 2.5 and not 2 but the function would have to be redone
    if x > 2:
        winrate = 1
    elif x < 0.4:
        winrate = 0
    else:
        winrate = (12.832883444301027*x**(11)-171.668262561212487*x**(10)+1018.533858483560834*x**(9)-3529.694284997589875*x**(8)+7918.373606722701879*x**(7)-12042.696852729619422 *
                   x**(6)+12637.399722721022044*x**(5)-9128.535790660698694*x**(4)+4437.651655224382012*x**(3)-1378.156072477675025*x**(2)+245.439740545813436*x-18.980551645186498)
    return winrate


async def battle_calc(self, nation1_id=None, nation2_id=None, nation1=None, nation2=None):
            def hide():
                results = {}

                if nation1 and nation1_id or nation2 and nation2_id:
                    raise Exception("You can't specify nation1 or nation2 multiple times!")
                if nation1:
                    results['nation1'] = nation1
                    nation1_id = nation1['id']
                if nation2:
                    results['nation2'] = nation2
                    nation2_id = nation2['id']
                if (nation1_id and not nation1) or (nation2_id and not nation2):
                    ids = []
                    if nation1_id:
                        ids.append(nation1_id)
                    if nation2_id:
                        ids.append(nation2_id)
                    nations = (await utils.call(f"{{nations(id:[{','.join(list(set(ids)))}]){{data{utils.get_query(queries.BATTLE_CALC)}}}}}"))['data']['nations']['data']
                    nations = sorted(nations, key=lambda x: int(x['id']))
                    for nation in nations:
                        if nation['id'] == nation1_id:
                            results['nation1'] = nation
                        if nation['id'] == nation2_id:
                            results['nation2'] = nation

                results['nation1_append'] = ""
                results['nation2_append'] = ""
                results['nation1_tanks'] = 1
                results['nation2_tanks'] = 1
                results['nation1_extra_cas'] = 1
                results['nation2_extra_cas'] = 1
                results['gc'] = None
                results['nation1_war_infra_mod'] = 0.5
                results['nation2_war_infra_mod'] = 0.5
                results['nation1_war_loot_mod'] = 0.5
                results['nation2_war_loot_mod'] = 0.5

                for war in results['nation1']['wars']:
                    if war['attid'] == nation2_id and war['turnsleft'] > 0 and war['defid'] == nation1_id:
                        if war['groundcontrol'] == nation1_id:
                            results['gc'] = results['nation1']
                            results['nation1_append'] += "<:small_gc:924988666613489685>"
                        elif war['groundcontrol'] == nation2_id:
                            results['gc'] = results['nation2']
                            results['nation2_append'] += "<:small_gc:924988666613489685>"
                        if war['airsuperiority'] == nation1_id:
                            results['nation2_tanks'] = 0.5
                            results['nation1_append'] += "<:small_air:924988666810601552>"
                        elif war['airsuperiority'] == nation2_id:
                            results['nation1_tanks'] = 0.5
                            results['nation2_append'] += "<:small_air:924988666810601552>"
                        if war['navalblockade'] == nation1_id: #blockade is opposite than the others
                            results['nation2_append'] += "<:small_blockade:924988666814808114>"
                        elif war['navalblockade'] == nation2_id:
                            results['nation1_append'] += "<:small_blockade:924988666814808114>"
                        if war['att_fortify']:
                            results['nation2_append'] += "<:fortified:925465012955385918>"
                            results['nation1_extra_cas'] = 1.25
                        if war['def_fortify']:
                            results['nation1_append'] += "<:fortified:925465012955385918>"
                            results['nation2_extra_cas'] = 1.25
                        if war['attpeace']:
                            results['nation2_append'] += "<:peace:926855240655990836>"
                        elif war['defpeace']:
                            results['nation1_append'] += "<:peace:926855240655990836>"
                        if war['war_type'] == "RAID":
                            results['nation2_war_infra_mod'] = 0.25
                            results['nation1_war_infra_mod'] = 0.5
                            results['nation2_war_loot_mod'] = 1
                            results['nation1_war_loot_mod'] = 1
                        elif war['war_type'] == "ORDINARY":
                            results['nation2_war_infra_mod'] = 0.5
                            results['nation1_war_infra_mod'] = 0.5
                            results['nation2_war_loot_mod'] = 0.5
                            results['nation1_war_loot_mod'] = 0.5
                        elif war['war_type'] == "ATTRITION":
                            results['nation2_war_infra_mod'] = 1
                            results['nation1_war_infra_mod'] = 1
                            results['nation2_war_loot_mod'] = 0.25
                            results['nation1_war_loot_mod'] = 0.5
                    elif war['defid'] == nation2_id and war['turnsleft'] > 0 and war['attid'] == nation1_id:
                        if war['groundcontrol'] == nation1_id:
                            results['gc'] = results['nation1']
                            results['nation1_append'] += "<:small_gc:924988666613489685>"
                        elif war['groundcontrol'] == nation2_id:
                            results['gc'] = results['nation2']
                            results['nation2_append'] += "<:small_gc:924988666613489685>"
                        if war['airsuperiority'] == nation1_id:
                            results['nation2_tanks'] = 0.5
                            results['nation1_append'] += "<:small_air:924988666810601552>"
                        elif war['airsuperiority'] == nation2_id:
                            results['nation1_tanks'] = 0.5
                            results['nation2_append'] += "<:small_air:924988666810601552>"
                        if war['navalblockade'] == nation1_id: #blockade is opposite than the others
                            results['nation2_append'] += "<:small_blockade:924988666814808114>"
                        elif war['navalblockade'] == nation2_id:
                            results['nation1_append'] += "<:small_blockade:924988666814808114>"
                        if war['att_fortify']:
                            results['nation1_append'] += "<:fortified:925465012955385918>"
                            results['nation2_extra_cas'] = 1.25
                        if war['def_fortify']:
                            results['nation2_append'] += "<:fortified:925465012955385918>"
                            results['nation1_extra_cas'] = 1.25
                        if war['attpeace']:
                            results['nation1_append'] += "<:peace:926855240655990836>"
                        elif war['defpeace']:
                            results['nation2_append'] += "<:peace:926855240655990836>"
                        if war['war_type'] == "RAID":
                            results['nation1_war_infra_mod'] = 0.25
                            results['nation2_war_infra_mod'] = 0.5
                            results['nation1_war_loot_mod'] = 1
                            results['nation2_war_loot_mod'] = 1
                        elif war['war_type'] == "ORDINARY":
                            results['nation1_war_infra_mod'] = 0.5
                            results['nation2_war_infra_mod'] = 0.5
                            results['nation1_war_loot_mod'] = 0.5
                            results['nation2_war_loot_mod'] = 0.5
                        elif war['war_type'] == "ATTRITION":
                            results['nation1_war_infra_mod'] = 1
                            results['nation2_war_infra_mod'] = 1
                            results['nation1_war_loot_mod'] = 0.25
                            results['nation2_war_loot_mod'] = 0.5
                
            for attacker, defender in [("nation1", "nation2"), ("nation2", "nation1")]:
                defender_tanks_value = (results[defender]['tanks'] * 40 * results[f'{defender}_tanks']) ** (3/4)
                defender_soldiers_value = (results[defender]['soldiers'] * 1.75 + results[defender]['population'] * 0.0025) ** (3/4)
                defender_army_value = (defender_soldiers_value + defender_tanks_value) ** (3/4)

                attacker_tanks_value = (results[attacker]['tanks'] * 40 * results[f'{attacker}_tanks']) ** (3/4)
                attacker_soldiers_value = (results[attacker]['soldiers'] * 1.75) ** (3/4)
                attacker_army_value = (attacker_soldiers_value + attacker_tanks_value) ** (3/4)

                results[f'{attacker}_ground_win_rate'] = self.winrate_calc(attacker_army_value, defender_army_value)
                results[f'{attacker}_ground_it'] = results[f'{attacker}_ground_win_rate']**3
                results[f'{attacker}_ground_mod'] = results[f'{attacker}_ground_win_rate']**2 * (1 - results[f'{attacker}_ground_win_rate']) * 3
                results[f'{attacker}_ground_pyr'] = results[f'{attacker}_ground_win_rate'] * (1 - results[f'{attacker}_ground_win_rate'])**2 * 3
                results[f'{attacker}_ground_fail'] = (1 - results[f'{attacker}_ground_win_rate'])**3

                attacker_aircraft_value = (results[attacker]['aircraft'] * 3) ** (3/4)
                defender_aircraft_value = (results[defender]['aircraft'] * 3) ** (3/4)
                results[f'{attacker}_air_win_rate'] = self.winrate_calc(attacker_aircraft_value, defender_aircraft_value)
                results[f'{attacker}_air_it'] = results[f'{attacker}_air_win_rate']**3
                results[f'{attacker}_air_mod'] = results[f'{attacker}_air_win_rate']**2 * (1 - results[f'{attacker}_air_win_rate']) * 3
                results[f'{attacker}_air_pyr'] = results[f'{attacker}_air_win_rate'] * (1 - results[f'{attacker}_air_win_rate'])**2 * 3
                results[f'{attacker}_air_fail'] = (1 - results[f'{attacker}_air_win_rate'])**3

                attacker_ships_value = (results[attacker]['ships'] * 4) ** (3/4)
                defender_ships_value = (results[defender]['ships'] * 4) ** (3/4)
                results[f'{attacker}_naval_win_rate'] = self.winrate_calc(attacker_ships_value, defender_ships_value)
                results[f'{attacker}_naval_it'] = results[f'{attacker}_naval_win_rate']**3
                results[f'{attacker}_naval_mod'] = results[f'{attacker}_naval_win_rate']**2 * (1 - results[f'{attacker}_naval_win_rate']) * 3
                results[f'{attacker}_naval_pyr'] = results[f'{attacker}_naval_win_rate'] * (1 - results[f'{attacker}_naval_win_rate'])**2 * 3
                results[f'{attacker}_naval_fail'] = (1 - results[f'{attacker}_naval_win_rate'])**3
                
                attacker_casualties_soldiers_value = utils.weird_division((attacker_soldiers_value**(4/3) + defender_soldiers_value**(4/3)) , (attacker_soldiers_value + defender_soldiers_value)) * attacker_soldiers_value
                defender_casualties_soldiers_value = utils.weird_division((attacker_soldiers_value**(4/3) + defender_soldiers_value**(4/3)) , (attacker_soldiers_value + defender_soldiers_value)) * defender_soldiers_value
                attacker_casualties_tanks_value = utils.weird_division((attacker_tanks_value**(4/3) + defender_tanks_value**(4/3)) , (attacker_tanks_value + defender_tanks_value)) * attacker_tanks_value
                defender_casualties_tanks_value = utils.weird_division((attacker_tanks_value**(4/3) + defender_tanks_value**(4/3)) , (attacker_tanks_value + defender_tanks_value)) * defender_tanks_value
                attacker_casualties_aircraft_value = utils.weird_division((attacker_aircraft_value**(4/3) + defender_aircraft_value**(4/3)) , (attacker_aircraft_value + defender_aircraft_value)) * attacker_aircraft_value
                defender_casualties_aircraft_value = utils.weird_division((attacker_aircraft_value**(4/3) + defender_aircraft_value**(4/3)) , (attacker_aircraft_value + defender_aircraft_value)) * defender_aircraft_value
                attacker_casualties_ships_value = utils.weird_division((attacker_ships_value**(4/3) + defender_ships_value**(4/3)) , (attacker_ships_value + defender_ships_value)) * attacker_ships_value
                defender_casualties_ships_value = utils.weird_division((attacker_ships_value**(4/3) + defender_ships_value**(4/3)) , (attacker_ships_value + defender_ships_value)) * defender_ships_value

                if results['gc'] == results[attacker]:
                    results[f'{attacker}_ground_{defender}_avg_aircraft'] = avg_air = round(min(results[attacker]['tanks'] * 0.005 * results[f'{attacker}_ground_win_rate'] ** 3, results[defender]['aircraft']))
                    results[defender]['aircas'] = f"Def. Plane: {avg_air} ± {round(results[attacker]['tanks'] * 0.005 * (1 - results[f'{attacker}_ground_win_rate'] ** 3))}"
                else:
                    results[defender]['aircas'] = ""
                    results[f'{attacker}_ground_{defender}_avg_aircraft'] = 0
                
                for type, cas_rate in [("avg", 0.7), ("diff", 0.3)]:
                    # values should be multiplied by 0.7 again? no... https://politicsandwar.fandom.com/wiki/Ground_Battles?so=search -> make a function for the average tank/soldier value roll giving success
                    results[f'{attacker}_ground_{attacker}_{type}_soldiers'] = min(round(((defender_casualties_soldiers_value * 0.0084) + (defender_casualties_tanks_value * 0.0092)) * cas_rate * 3), results[attacker]['soldiers'])
                    results[f'{attacker}_ground_{attacker}_{type}_tanks'] = min(round((((defender_casualties_soldiers_value * 0.0004060606) + (defender_casualties_tanks_value * 0.00066666666)) * results[f'{attacker}_ground_win_rate'] + ((defender_soldiers_value * 0.00043225806) + (defender_tanks_value * 0.00070967741)) * (1 - results[f'{attacker}_ground_win_rate'])) * cas_rate * 3), results[attacker]['tanks'])
                    results[f'{attacker}_ground_{defender}_{type}_soldiers'] = min(round(((attacker_casualties_soldiers_value * 0.0084) + (attacker_casualties_tanks_value * 0.0092)) * cas_rate * 3), results[defender]['soldiers'])
                    results[f'{attacker}_ground_{defender}_{type}_tanks'] = min(round((((attacker_casualties_soldiers_value * 0.00043225806) + (attacker_casualties_tanks_value * 0.00070967741)) * results[f'{attacker}_ground_win_rate'] + ((attacker_soldiers_value * 0.0004060606) + (attacker_tanks_value * 0.00066666666)) * (1 - results[f'{attacker}_ground_win_rate'])) * cas_rate * 3), results[defender]['tanks'])

                results[f'{attacker}_airvair_{attacker}_avg'] = min(round(defender_casualties_aircraft_value * 0.7 * 0.01 * 3 * results[f'{attacker}_extra_cas']), results[attacker]['aircraft'])
                results[f'{attacker}_airvair_{attacker}_diff'] = min(round(defender_casualties_aircraft_value * 0.3 * 0.01 * 3 * results[f'{attacker}_extra_cas']), results[attacker]['aircraft'])
                results[f'{attacker}_airvother_{attacker}_avg'] = min(round(defender_casualties_aircraft_value * 0.7 * 0.015385 * 3 * results[f'{attacker}_extra_cas']), results[attacker]['aircraft'])
                results[f'{attacker}_airvother_{attacker}_diff'] = min(round(defender_casualties_aircraft_value * 0.3 * 0.015385 * 3 * results[f'{attacker}_extra_cas']), results[attacker]['aircraft'])

                results[f'{attacker}_airvair_{defender}_avg'] = min(round(attacker_casualties_aircraft_value * 0.7 * 0.018337 * 3), results[defender]['aircraft'])
                results[f'{attacker}_airvair_{defender}_diff'] = min(round(attacker_casualties_aircraft_value * 0.3 * 0.018337 * 3), results[defender]['aircraft'])
                results[f'{attacker}_airvother_{defender}_avg'] = min(round(attacker_casualties_aircraft_value * 0.7 * 0.009091 * 3), results[defender]['aircraft'])
                results[f'{attacker}_airvother_{defender}_diff'] = min(round(attacker_casualties_aircraft_value * 0.3 * 0.009091 * 3), results[defender]['aircraft'])

                results[f'{attacker}_naval_{defender}_avg'] = min(round(attacker_casualties_ships_value * 0.7 * 0.01375 * 3 * results[f'{attacker}_extra_cas']), results[defender]['aircraft'])
                results[f'{attacker}_naval_{defender}_diff'] = min(round(attacker_casualties_ships_value * 0.3 * 0.01375 * 3 * results[f'{attacker}_extra_cas']), results[defender]['aircraft'])
                results[f'{attacker}_naval_{attacker}_avg'] = min(round(defender_casualties_ships_value * 0.7 * 0.01375 * 3), results[attacker]['aircraft'])
                results[f'{attacker}_naval_{attacker}_diff'] = min(round(defender_casualties_ships_value * 0.3 * 0.01375 * 3), results[attacker]['aircraft'])

            def def_rss_consumption(winrate: Union[int, float]) -> float:
                rate = -0.4624 * winrate**2 + 1.06256 * winrate + 0.3999            
                if rate < 0.4:
                    rate = 0.4
                return rate
                ## See note

            results["nation1"]['city'] = sorted(results['nation1']['cities'], key=lambda k: k['infrastructure'], reverse=True)[0]
            results["nation2"]['city'] = sorted(results['nation2']['cities'], key=lambda k: k['infrastructure'], reverse=True)[0]

            for nation in ["nation1", "nation2"]:
                results[f'{nation}_policy_infra_dealt'] = 1
                results[f'{nation}_policy_loot_stolen'] = 1
                results[f'{nation}_policy_infra_lost'] = 1
                results[f'{nation}_policy_loot_lost'] = 1
                results[f'{nation}_policy_improvements_lost'] = 1
                results[f'{nation}_policy_loot_stolen'] = 1
                results[f'{nation}_policy_improvements_destroyed'] = 1
                results[f'{nation}_vds_mod'] = 1
                results[f'{nation}_irond_mod'] = 1
                results[f'{nation}_fallout_shelter_mod'] = 1
                results[f'{nation}_military_salvage_mod'] = 0
                results[f'{nation}_pirate_econ_loot'] = 1
                results[f'{nation}_advanced_pirate_econ_loot'] = 1

                if results[f'{nation}']['warpolicy'] == "Attrition":
                    results[f'{nation}_policy_infra_dealt'] = 1.1
                    results[f'{nation}_policy_loot_stolen'] = 0.8
                elif results[f'{nation}']['warpolicy'] == "Turtle":
                    results[f'{nation}_policy_infra_lost'] = 0.9
                    results[f'{nation}_policy_loot_lost'] = 1.2
                elif results[f'{nation}']['warpolicy'] == "Moneybags":
                    results[f'{nation}_policy_infra_lost'] = 1.05
                    results[f'{nation}_policy_loot_lost'] = 0.6
                elif results[f'{nation}']['warpolicy'] == "Pirate":
                    results[f'{nation}_policy_improvements_lost'] = 2.0
                    results[f'{nation}_policy_loot_stolen'] = 1.4
                elif results[f'{nation}']['warpolicy'] == "Tactician":
                    results[f'{nation}_policy_improvements_destroyed'] = 2.0
                elif results[f'{nation}']['warpolicy'] == "Guardian":
                    results[f'{nation}_policy_improvements_lost'] = 0.5
                    results[f'{nation}_policy_loot_lost'] = 1.2
                elif results[f'{nation}']['warpolicy'] == "Covert":
                    results[f'{nation}_policy_infra_lost'] = 1.05
                elif results[f'{nation}']['warpolicy'] == "Arcane":
                    results[f'{nation}_policy_infra_lost'] = 1.05
                if results[f'{nation}']['vds']:
                    results[f'{nation}_vds_mod'] = 0.75
                if results[f'{nation}']['irond']:
                    results[f'{nation}_irond_mod'] = 0.7
                if results[f'{nation}']['fallout_shelter']:
                    results[f'{nation}_fallout_shelter_mod'] = 0.9
                if results[f'{nation}']['military_salvage']:
                    results[f'{nation}_military_salvage_mod'] = 1
                if results[f'{nation}']['pirate_economy']:
                    results[f'{nation}_pirate_econ_loot'] = 1.05
                if results[f'{nation}']['advanced_pirate_economy']:
                    results[f'{nation}_advanced_pirate_econ_loot'] = 1.05
            
            def airstrike_casualties(winrate: Union[int, float]) -> float:
                rate = -0.4624 * winrate**2 + 1.06256 * winrate + 0.3999            
                if rate < 0.4:
                    rate = 0.4
                return rate
            
            def salvage(winrate, resources) -> int:
                return resources * (results[f'{attacker}_military_salvage_mod'] * (winrate ** 3) * 0.05)

            for attacker, defender in [("nation1", "nation2"), ("nation2", "nation1")]:
                results[f'{attacker}_ground_{defender}_lost_infra_avg'] = max(min(((results[attacker]['soldiers'] - results[defender]['soldiers'] * 0.5) * 0.000606061 + (results[attacker]['tanks'] - (results[defender]['tanks'] * 0.5)) * 0.01) * 0.95 * results[f'{attacker}_ground_win_rate'], results[defender]['city']['infrastructure'] * 0.2 + 25), 0) * results[f'{attacker}_war_infra_mod'] * results[f'{attacker}_policy_infra_dealt'] * results[f'{defender}_policy_infra_lost']
                results[f'{attacker}_ground_{defender}_lost_infra_diff'] = results[f'{attacker}_ground_{defender}_lost_infra_avg'] / 0.95 * 0.15
                results[f'{attacker}_ground_loot_avg'] = (results[attacker]['soldiers'] * 1.1 + results[attacker]['tanks'] * 25.15) * (results[f'{attacker}_ground_win_rate'] ** 3) * 3 * 0.95 * results[f'{attacker}_war_loot_mod'] * results[f'{attacker}_policy_loot_stolen'] * results[f'{defender}_policy_loot_lost'] * results[f'{attacker}_pirate_econ_loot'] * results[f'{attacker}_advanced_pirate_econ_loot']
                results[f'{attacker}_ground_loot_diff'] = results[f'{attacker}_ground_loot_avg'] / 0.95 * 0.1

                results[f'{attacker}_air_{defender}_lost_infra_avg'] = max(min((results[attacker]['aircraft'] - results[defender]['aircraft'] * 0.5) * 0.35353535 * 0.95 * results[f'{attacker}_air_win_rate'], results[defender]['city']['infrastructure'] * 0.5 + 100), 0) * results[f'{attacker}_war_infra_mod'] * results[f'{attacker}_policy_infra_dealt'] * results[f'{defender}_policy_infra_lost']
                results[f'{attacker}_air_{defender}_lost_infra_diff'] = results[f'{attacker}_air_{defender}_lost_infra_avg'] / 0.95 * 0.15
                results[f'{attacker}_air_{defender}_soldiers_destroyed_avg'] = round(max(min(results[defender]['soldiers'], results[defender]['soldiers'] * 0.75 + 1000, (results[attacker]['aircraft'] - results[defender]['aircraft'] * 0.5) * 35 * 0.95), 0)) * airstrike_casualties(results[f'{attacker}_air_win_rate'])
                results[f'{attacker}_air_{defender}_soldiers_destroyed_diff'] = results[f'{attacker}_air_{defender}_soldiers_destroyed_avg'] / 0.95 * 0.1
                results[f'{attacker}_air_{defender}_tanks_destroyed_avg'] = round(max(min(results[defender]['tanks'], results[defender]['tanks'] * 0.75 + 10, (results[attacker]['aircraft'] - results[defender]['aircraft'] * 0.5) * 1.25 * 0.95), 0)) * airstrike_casualties(results[f'{attacker}_air_win_rate'])
                results[f'{attacker}_air_{defender}_tanks_destroyed_diff'] = results[f'{attacker}_air_{defender}_tanks_destroyed_avg'] / 0.95 * 0.1
                results[f'{attacker}_air_{defender}_ships_destroyed_avg'] = round(max(min(results[defender]['ships'], results[defender]['ships'] * 0.75 + 4, (results[attacker]['aircraft'] - results[defender]['aircraft'] * 0.5) * 0.0285 * 0.95), 0)) * airstrike_casualties(results[f'{attacker}_air_win_rate'])
                results[f'{attacker}_air_{defender}_ships_destroyed_diff'] = results[f'{attacker}_air_{defender}_ships_destroyed_avg'] / 0.95 * 0.1

                results[f'{attacker}_naval_{defender}_lost_infra_avg'] = max(min((results[attacker]['ships'] - results[attacker]['ships'] * 0.5) * 2.625 * 0.95 * results[f'{attacker}_naval_win_rate'], results[defender]['city']['infrastructure'] * 0.5 + 25), 0) * results[f'{attacker}_war_infra_mod'] * results[f'{attacker}_policy_infra_dealt'] * results[f'{defender}_policy_infra_lost']
                results[f'{attacker}_naval_{defender}_lost_infra_diff'] = results[f'{attacker}_naval_{defender}_lost_infra_avg'] / 0.95 * 0.15

                results[f'{attacker}_nuke_{defender}_lost_infra_avg'] = max(min((1700 + max(2000, results[defender]['city']['infrastructure'] * 100 / results[defender]['city']['land'] * 13.5)) / 2, results[defender]['city']['infrastructure'] * 0.8 + 150), 0) * results[f'{attacker}_war_infra_mod'] * results[f'{attacker}_policy_infra_dealt'] * results[f'{defender}_policy_infra_lost'] * results[f'{defender}_fallout_shelter_mod']
                results[f'{attacker}_missile_{defender}_lost_infra_avg'] = max(min((300 + max(350, results[defender]['city']['infrastructure'] * 100 / results[defender]['city']['land'] * 3)) / 2, results[defender]['city']['infrastructure'] * 0.3 + 100), 0) * results[f'{attacker}_war_infra_mod'] * results[f'{attacker}_policy_infra_dealt'] * results[f'{defender}_policy_infra_lost']
                
                for infra in [
                        f"{attacker}_ground_{defender}_lost_infra",
                        f"{attacker}_air_{defender}_lost_infra",
                        f"{attacker}_naval_{defender}_lost_infra",
                        f"{attacker}_nuke_{defender}_lost_infra",
                        f"{attacker}_missile_{defender}_lost_infra",
                    ]:
                    if "missile" in infra:
                        modifier = results[f'{defender}_irond_mod']
                    elif "nuke" in infra:
                        modifier = results[f'{defender}_vds_mod']
                    else:
                        modifier = 1
                    results[f'{infra}_avg_value'] = utils.infra_cost(results[defender]['city']['infrastructure'] - results[f'{infra}_avg'], results[defender]['city']['infrastructure']) * modifier
                
                for attack in ['airvair', 'airvsoldiers', 'airvtanks', 'airvships']:
                    results[f"{attacker}_{attack}_{defender}_lost_infra_avg_value"] = results[f"{attacker}_air_{defender}_lost_infra_avg_value"] * 1/3
                results[f"{attacker}_airvinfra_{defender}_lost_infra_avg_value"] = results[f"{attacker}_air_{defender}_lost_infra_avg_value"]


                results[f'{attacker}_ground_{attacker}_mun'] = results[attacker]['soldiers'] * 0.0002 + results[attacker]['tanks'] * 0.01
                results[f'{attacker}_ground_{attacker}_gas'] = results[attacker]['tanks'] * 0.01
                results[f'{attacker}_ground_{attacker}_alum'] = 0 #-salvage(results[f'{attacker}_ground_win_rate'], results[f'{attacker}_ground_{defender}_alum']) 
                results[f'{attacker}_ground_{attacker}_steel'] = results[f'{attacker}_ground_{attacker}_avg_tanks'] * 0.5 - salvage(results[f'{attacker}_ground_win_rate'], results[f'{attacker}_ground_{attacker}_avg_tanks'] * 0.5) - salvage(results[f'{attacker}_ground_win_rate'], results[f'{attacker}_ground_{defender}_avg_tanks'] * 0.5)
                results[f'{attacker}_ground_{attacker}_money'] = -results[f'{attacker}_ground_loot_avg'] + results[f'{attacker}_ground_{attacker}_avg_tanks'] * 50 + results[f'{attacker}_ground_{attacker}_avg_soldiers'] * 5
                results[f'{attacker}_ground_{attacker}_total'] = results[f'{attacker}_ground_{attacker}_alum'] * 2971 + results[f'{attacker}_ground_{attacker}_steel'] * 3990 + results[f'{attacker}_ground_{attacker}_gas'] * 3340 + results[f'{attacker}_ground_{attacker}_mun'] * 1960 + results[f'{attacker}_ground_{attacker}_money'] 

                base_mun = (results[defender]['soldiers'] * 0.0002 + results[defender]['population'] / 2000000 + results[defender]['tanks'] * 0.01) * def_rss_consumption(results[f'{attacker}_ground_win_rate'])
                results[f'{attacker}_ground_{defender}_mun'] = (base_mun * (1 - results[f'{attacker}_ground_fail']) + min(base_mun, results[f'{attacker}_ground_{attacker}_mun']) * results[f'{attacker}_ground_fail'])
                base_gas = results[defender]['tanks'] * 0.01 * def_rss_consumption(results[f'{attacker}_ground_win_rate'])
                results[f'{attacker}_ground_{defender}_gas'] = (base_gas * (1 - results[f'{attacker}_ground_fail']) + min(base_gas, results[f'{attacker}_ground_{attacker}_gas']) * results[f'{attacker}_ground_fail'])
                results[f'{attacker}_ground_{defender}_alum'] = results[f'{attacker}_ground_{defender}_avg_aircraft'] * 5
                results[f'{attacker}_ground_{defender}_steel'] = results[f'{attacker}_ground_{defender}_avg_tanks'] * 0.5
                results[f'{attacker}_ground_{defender}_money'] = results[f'{attacker}_ground_loot_avg'] + results[f'{attacker}_ground_{defender}_avg_aircraft'] * 4000 + results[f'{attacker}_ground_{defender}_avg_tanks'] * 50 + results[f'{attacker}_ground_{defender}_avg_soldiers'] * 5 + results[f'{attacker}_ground_{defender}_lost_infra_avg_value']
                results[f'{attacker}_ground_{defender}_total'] = results[f'{attacker}_ground_{defender}_alum'] * 2971 + results[f'{attacker}_ground_{defender}_steel'] * 3990 + results[f'{attacker}_ground_{defender}_gas'] * 3340 + results[f'{attacker}_ground_{defender}_mun'] * 1960 + results[f'{attacker}_ground_{defender}_money'] 
                results[f'{attacker}_ground_net'] = results[f'{attacker}_ground_{defender}_total'] - results[f'{attacker}_ground_{attacker}_total']
                

                for attack in ['air', 'airvair', 'airvinfra', 'airvsoldiers', 'airvtanks', 'airvships']:
                    results[f'{attacker}_{attack}_{attacker}_gas'] = results[f'{attacker}_{attack}_{attacker}_mun'] = results[attacker]['aircraft'] / 4
                    base_gas = results[defender]['aircraft'] / 4 * def_rss_consumption(results[f'{attacker}_air_win_rate'])
                    results[f'{attacker}_{attack}_{defender}_gas'] = results[f'{attacker}_{attack}_{defender}_mun'] = (base_gas * (1 - results[f'{attacker}_air_fail']) + min(base_gas, results[f'{attacker}_air_{attacker}_gas']) * results[f'{attacker}_air_fail'])

                results[f'{attacker}_airvair_{attacker}_alum'] = results[f'{attacker}_airvair_{attacker}_avg'] * 5 - salvage(results[f'{attacker}_air_win_rate'], results[f'{attacker}_airvair_{attacker}_avg'] * 5) - salvage(results[f'{attacker}_air_win_rate'], results[f'{attacker}_airvair_{defender}_avg'] * 5)
                results[f'{attacker}_airvair_{attacker}_steel'] = 0
                results[f'{attacker}_airvair_{attacker}_money'] = results[f'{attacker}_airvair_{attacker}_avg'] * 4000
                results[f'{attacker}_airvair_{attacker}_total'] = results[f'{attacker}_airvair_{attacker}_alum'] * 2971 + results[f'{attacker}_airvair_{attacker}_steel'] * 3990 + results[f'{attacker}_air_{attacker}_gas'] * 3340 + results[f'{attacker}_air_{attacker}_mun'] * 1960 + results[f'{attacker}_airvair_{attacker}_money'] 
               
                results[f'{attacker}_airvair_{defender}_alum'] = results[f'{attacker}_airvair_{defender}_avg'] * 5
                results[f'{attacker}_airvair_{defender}_steel'] = 0
                results[f'{attacker}_airvair_{defender}_money'] = results[f'{attacker}_airvair_{defender}_avg'] * 4000 + results[f'{attacker}_air_{defender}_lost_infra_avg_value'] * 1/3
                results[f'{attacker}_airvair_{defender}_total'] = results[f'{attacker}_airvair_{defender}_alum'] * 2971 + results[f'{attacker}_airvair_{defender}_steel'] * 3990 + results[f'{attacker}_air_{defender}_gas'] * 3340 + results[f'{attacker}_air_{defender}_mun'] * 1960 + results[f'{attacker}_airvair_{defender}_money'] 
                results[f'{attacker}_airvair_net'] = results[f'{attacker}_airvair_{defender}_total'] - results[f'{attacker}_airvair_{attacker}_total']


                results[f'{attacker}_airvinfra_{attacker}_alum'] = results[f'{attacker}_airvother_{attacker}_avg'] * 5 - salvage(results[f'{attacker}_air_win_rate'], results[f'{attacker}_airvother_{attacker}_avg'] * 5) - salvage(results[f'{attacker}_air_win_rate'], results[f'{attacker}_airvother_{defender}_avg'] * 5)
                results[f'{attacker}_airvinfra_{attacker}_steel'] = 0
                results[f'{attacker}_airvinfra_{attacker}_money'] = results[f'{attacker}_airvother_{attacker}_avg'] * 4000
                results[f'{attacker}_airvinfra_{attacker}_total'] = results[f'{attacker}_airvinfra_{attacker}_alum'] * 2971 + results[f'{attacker}_airvinfra_{attacker}_steel'] * 3990 + results[f'{attacker}_air_{attacker}_gas'] * 3340 + results[f'{attacker}_air_{attacker}_mun'] * 1960 + results[f'{attacker}_airvinfra_{attacker}_money'] 

                results[f'{attacker}_airvinfra_{defender}_alum'] = results[f'{attacker}_airvother_{defender}_avg'] * 5
                results[f'{attacker}_airvinfra_{defender}_steel'] = 0
                results[f'{attacker}_airvinfra_{defender}_money'] = results[f'{attacker}_airvother_{defender}_avg'] * 4000 + results[f'{attacker}_air_{defender}_lost_infra_avg_value']
                results[f'{attacker}_airvinfra_{defender}_total'] = results[f'{attacker}_airvinfra_{defender}_alum'] * 2971 + results[f'{attacker}_airvinfra_{defender}_steel'] * 3990 + results[f'{attacker}_air_{defender}_gas'] * 3340 + results[f'{attacker}_air_{defender}_mun'] * 1960 + results[f'{attacker}_airvinfra_{defender}_money'] 
                results[f'{attacker}_airvinfra_net'] = results[f'{attacker}_airvinfra_{defender}_total'] - results[f'{attacker}_airvinfra_{attacker}_total']


                results[f'{attacker}_airvsoldiers_{attacker}_alum'] = results[f'{attacker}_airvother_{attacker}_avg'] * 5 - salvage(results[f'{attacker}_air_win_rate'], results[f'{attacker}_airvother_{attacker}_avg'] * 5) - salvage(results[f'{attacker}_air_win_rate'], results[f'{attacker}_airvother_{defender}_avg'] * 5)
                results[f'{attacker}_airvsoldiers_{attacker}_steel'] = 0
                results[f'{attacker}_airvsoldiers_{attacker}_money'] = results[f'{attacker}_airvother_{attacker}_avg'] * 4000
                results[f'{attacker}_airvsoldiers_{attacker}_total'] = results[f'{attacker}_airvsoldiers_{attacker}_alum'] * 2971 + results[f'{attacker}_airvsoldiers_{attacker}_steel'] * 3990 + results[f'{attacker}_air_{attacker}_gas'] * 3340 + results[f'{attacker}_air_{attacker}_mun'] * 1960 + results[f'{attacker}_airvsoldiers_{attacker}_money'] 
                
                results[f'{attacker}_airvsoldiers_{defender}_alum'] = results[f'{attacker}_airvother_{defender}_avg'] * 5
                results[f'{attacker}_airvsoldiers_{defender}_steel'] = 0
                results[f'{attacker}_airvsoldiers_{defender}_money'] = results[f'{attacker}_airvother_{defender}_avg'] * 4000 + results[f'{attacker}_air_{defender}_lost_infra_avg_value'] * 1/3 + results[f'{attacker}_air_{defender}_soldiers_destroyed_avg'] * 5
                results[f'{attacker}_airvsoldiers_{defender}_total'] = results[f'{attacker}_airvsoldiers_{defender}_alum'] * 2971 + results[f'{attacker}_airvsoldiers_{defender}_steel'] * 3990 + results[f'{attacker}_air_{defender}_gas'] * 3340 + results[f'{attacker}_air_{defender}_mun'] * 1960 + results[f'{attacker}_airvsoldiers_{defender}_money'] 
                results[f'{attacker}_airvsoldiers_net'] = results[f'{attacker}_airvair_{defender}_total'] - results[f'{attacker}_airvsoldiers_{attacker}_total']
                

                results[f'{attacker}_airvtanks_{attacker}_alum'] = results[f'{attacker}_airvother_{attacker}_avg'] * 5 - salvage(results[f'{attacker}_air_win_rate'], results[f'{attacker}_airvother_{attacker}_avg'] * 5) - salvage(results[f'{attacker}_air_win_rate'], results[f'{attacker}_airvother_{defender}_avg'] * 5)
                results[f'{attacker}_airvtanks_{attacker}_steel'] = 0
                results[f'{attacker}_airvtanks_{attacker}_money'] = results[f'{attacker}_airvother_{attacker}_avg'] * 4000
                results[f'{attacker}_airvtanks_{attacker}_total'] = results[f'{attacker}_airvtanks_{attacker}_alum'] * 2971 + results[f'{attacker}_airvtanks_{attacker}_steel'] * 3990 + results[f'{attacker}_air_{attacker}_gas'] * 3340 + results[f'{attacker}_air_{attacker}_mun'] * 1960 + results[f'{attacker}_airvtanks_{attacker}_money'] 

                results[f'{attacker}_airvtanks_{defender}_alum'] = results[f'{attacker}_airvother_{defender}_avg'] * 5
                results[f'{attacker}_airvtanks_{defender}_steel'] = results[f'{attacker}_air_{defender}_tanks_destroyed_avg'] * 0.5
                results[f'{attacker}_airvtanks_{defender}_money'] = results[f'{attacker}_airvother_{defender}_avg'] * 4000 + results[f'{attacker}_air_{defender}_lost_infra_avg_value'] * 1/3 + results[f'{attacker}_air_{defender}_tanks_destroyed_avg'] * 60
                results[f'{attacker}_airvtanks_{defender}_total'] = results[f'{attacker}_airvtanks_{defender}_alum'] * 2971 + results[f'{attacker}_airvtanks_{defender}_steel'] * 3990 + results[f'{attacker}_air_{defender}_gas'] * 3340 + results[f'{attacker}_air_{defender}_mun'] * 1960 + results[f'{attacker}_airvtanks_{defender}_money'] 
                results[f'{attacker}_airvtanks_net'] = results[f'{attacker}_airvtanks_{defender}_total'] - results[f'{attacker}_airvtanks_{attacker}_total']


                results[f'{attacker}_airvships_{attacker}_alum'] = results[f'{attacker}_airvother_{attacker}_avg'] * 5 - salvage(results[f'{attacker}_air_win_rate'], results[f'{attacker}_airvother_{attacker}_avg'] * 5) - salvage(results[f'{attacker}_air_win_rate'], results[f'{attacker}_airvother_{defender}_avg'] * 5)
                results[f'{attacker}_airvships_{attacker}_steel'] = 0
                results[f'{attacker}_airvships_{attacker}_money'] = results[f'{attacker}_airvother_{attacker}_avg'] * 4000
                results[f'{attacker}_airvships_{attacker}_total'] = results[f'{attacker}_airvships_{attacker}_alum'] * 2971 + results[f'{attacker}_airvships_{attacker}_steel'] * 3990 + results[f'{attacker}_air_{attacker}_gas'] * 3340 + results[f'{attacker}_air_{attacker}_mun'] * 1960 + results[f'{attacker}_airvships_{attacker}_money'] 
                
                results[f'{attacker}_airvships_{defender}_alum'] = results[f'{attacker}_airvother_{defender}_avg'] * 5
                results[f'{attacker}_airvships_{defender}_steel'] = results[f'{attacker}_air_{defender}_ships_destroyed_avg'] * 30
                results[f'{attacker}_airvships_{defender}_money'] = results[f'{attacker}_airvother_{defender}_avg'] * 4000 + results[f'{attacker}_air_{defender}_lost_infra_avg_value'] * 1/3 + results[f'{attacker}_air_{defender}_ships_destroyed_avg'] * 50000
                results[f'{attacker}_airvships_{defender}_total'] = results[f'{attacker}_airvships_{defender}_alum'] * 2971 + results[f'{attacker}_airvships_{defender}_steel'] * 3990 + results[f'{attacker}_air_{defender}_gas'] * 3340 + results[f'{attacker}_air_{defender}_mun'] * 1960 + results[f'{attacker}_airvships_{defender}_money'] 
                results[f'{attacker}_airvships_net'] = results[f'{attacker}_airvships_{defender}_total'] - results[f'{attacker}_airvships_{attacker}_total']


                results[f'{attacker}_naval_{attacker}_mun'] = results[attacker]['ships'] * 2.5
                results[f'{attacker}_naval_{attacker}_gas'] = results[attacker]['ships'] * 1.5
                results[f'{attacker}_naval_{attacker}_alum'] = 0
                results[f'{attacker}_naval_{attacker}_steel'] = results[f'{attacker}_naval_{attacker}_avg'] * 30 + salvage(results[f'{attacker}_naval_win_rate'], results[f'{attacker}_naval_{attacker}_avg'] * 30) + salvage(results[f'{attacker}_naval_win_rate'], results[f'{attacker}_naval_{defender}_avg'] * 30)
                results[f'{attacker}_naval_{attacker}_money'] = results[f'{attacker}_naval_{attacker}_avg'] * 50000
                results[f'{attacker}_naval_{attacker}_total'] = results[f'{attacker}_naval_{attacker}_alum'] * 2971 + results[f'{attacker}_naval_{attacker}_steel'] * 3990 + results[f'{attacker}_naval_{attacker}_gas'] * 3340 + results[f'{attacker}_naval_{attacker}_mun'] * 1960 + results[f'{attacker}_naval_{attacker}_money'] 
            
                base_mun = results[defender]['ships'] * 2.5 * def_rss_consumption(results[f'{attacker}_naval_win_rate'])
                results[f'{attacker}_naval_{defender}_mun'] = results[f'{attacker}_naval_{defender}_mun'] = (base_mun * (1 - results[f'{attacker}_naval_fail']) + min(base_gas, results[f'{attacker}_naval_{attacker}_mun']) * results[f'{attacker}_naval_fail'])
                base_gas = results[defender]['ships'] * 1.5 * def_rss_consumption(results[f'{attacker}_naval_win_rate'])
                results[f'{attacker}_naval_{defender}_gas'] = results[f'{attacker}_naval_{defender}_gas'] = (base_gas * (1 - results[f'{attacker}_naval_fail']) + min(base_gas, results[f'{attacker}_naval_{attacker}_gas']) * results[f'{attacker}_naval_fail'])
                results[f'{attacker}_naval_{defender}_alum'] = 0
                results[f'{attacker}_naval_{defender}_steel'] = results[f'{attacker}_naval_{defender}_avg'] * 30
                results[f'{attacker}_naval_{defender}_money'] = results[f'{attacker}_naval_{defender}_lost_infra_avg_value'] + results[f'{attacker}_naval_{defender}_avg'] * 50000
                results[f'{attacker}_naval_{defender}_total'] = results[f'{attacker}_naval_{defender}_alum'] * 2971 + results[f'{attacker}_naval_{defender}_steel'] * 3990 + results[f'{attacker}_naval_{defender}_gas'] * 3340 + results[f'{attacker}_naval_{defender}_mun'] * 1960 + results[f'{attacker}_naval_{defender}_money'] 
                results[f'{attacker}_naval_net'] = results[f'{attacker}_naval_{defender}_total'] - results[f'{attacker}_naval_{attacker}_total']


                results[f'{attacker}_nuke_{attacker}_alum'] = 750
                results[f'{attacker}_nuke_{attacker}_steel'] = 0
                results[f'{attacker}_nuke_{attacker}_gas'] = 500
                results[f'{attacker}_nuke_{attacker}_mun'] = 0
                results[f'{attacker}_nuke_{attacker}_money'] = 1750000
                results[f'{attacker}_nuke_{attacker}_total'] = results[f'{attacker}_nuke_{attacker}_alum'] * 2971 + results[f'{attacker}_nuke_{attacker}_steel'] * 3990 + results[f'{attacker}_nuke_{attacker}_gas'] * 3340 + results[f'{attacker}_nuke_{attacker}_mun'] * 1960 + results[f'{attacker}_nuke_{attacker}_money'] + 250 * 3039 #price of uranium
                
                results[f'{attacker}_nuke_{defender}_alum'] = 0
                results[f'{attacker}_nuke_{defender}_steel'] = 0
                results[f'{attacker}_nuke_{defender}_gas'] = 0
                results[f'{attacker}_nuke_{defender}_mun'] = 0
                results[f'{attacker}_nuke_{defender}_money'] = results[f'{attacker}_nuke_{defender}_lost_infra_avg_value']
                results[f'{attacker}_nuke_{defender}_total'] = results[f'{attacker}_nuke_{defender}_alum'] * 2971 + results[f'{attacker}_nuke_{defender}_steel'] * 3990 + results[f'{attacker}_nuke_{defender}_gas'] * 3340 + results[f'{attacker}_nuke_{defender}_mun'] * 1960 + results[f'{attacker}_nuke_{defender}_money'] 
                results[f'{attacker}_nuke_net'] = results[f'{attacker}_nuke_{defender}_total'] - results[f'{attacker}_nuke_{attacker}_total']


                results[f'{attacker}_missile_{attacker}_alum'] = 100
                results[f'{attacker}_missile_{attacker}_steel'] = 0
                results[f'{attacker}_missile_{attacker}_gas'] = 75
                results[f'{attacker}_missile_{attacker}_mun'] = 75
                results[f'{attacker}_missile_{attacker}_money'] = 150000
                results[f'{attacker}_missile_{attacker}_total'] = results[f'{attacker}_missile_{attacker}_alum'] * 2971 + results[f'{attacker}_missile_{attacker}_steel'] * 3990 + results[f'{attacker}_missile_{attacker}_gas'] * 3340 + results[f'{attacker}_missile_{attacker}_mun'] * 1960 + results[f'{attacker}_missile_{attacker}_money']

                results[f'{attacker}_missile_{defender}_alum'] = 0
                results[f'{attacker}_missile_{defender}_steel'] = 0
                results[f'{attacker}_missile_{defender}_gas'] = 0
                results[f'{attacker}_missile_{defender}_mun'] = 0
                results[f'{attacker}_missile_{defender}_money'] = results[f'{attacker}_missile_{defender}_lost_infra_avg_value']
                results[f'{attacker}_missile_{defender}_total'] = results[f'{attacker}_missile_{defender}_alum'] * 2971 + results[f'{attacker}_missile_{defender}_steel'] * 3990 + results[f'{attacker}_missile_{defender}_gas'] * 3340 + results[f'{attacker}_missile_{defender}_mun'] * 1960 + results[f'{attacker}_missile_{defender}_money'] 
                results[f'{attacker}_missile_net'] = results[f'{attacker}_missile_{defender}_total'] - results[f'{attacker}_missile_{attacker}_total']
                
            return results
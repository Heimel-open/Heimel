import hashlib
import json
from pathlib import Path

def create_task_definitions():
    families = []

    # TIER 1: Local / Short-Horizon (L01-L12)
    tier1_specs = [
        {
            'id': 'L01',
            'name': 'Bakery Loaves Distribution',
            'prompt_core': 'A bakery produces 6 trays of 14 artisan loaves. 19 loaves are packaged for delivery. An unused auxiliary backup oven with a capacity of 30 loaves remains powered off. How many loaves remain unpackaged?',
            'components': [
                {'id': 'C1', 'name': 'tray_production', 'role': 'MATERIAL_ACTIVE', 'value': 84, 'is_material': True, 'requires_restore': False},
                {'id': 'C2', 'name': 'delivery_packaging', 'role': 'MATERIAL_ACTIVE', 'value': 65, 'is_material': True, 'requires_restore': False},
                {'id': 'C3', 'name': 'backup_oven_capacity', 'role': 'DECOY_DISPENSABLE', 'value': 30, 'is_material': False, 'requires_restore': False},
            ],
            'required_intermediates': [84],
            'answer': 65,
            'edges': ['tray_production: 6 * 14 -> 84', 'packaging_deduction: 84 - 19 -> 65'],
            'consequence_step': None,
            'restore_targets': [],
            'decoy_components': ['C3'],
            'terminal_components': [],
        },
        {
            'id': 'L02',
            'name': 'Warehouse Staging Area',
            'prompt_core': 'A warehouse staging area receives 8 pallets holding 15 crates each. 34 crates are loaded onto a distribution van. An adjoining storage bay holding 40 empty pallets is reserved for next week. How many crates remain in the staging area?',
            'components': [
                {'id': 'C1', 'name': 'pallet_intake', 'role': 'MATERIAL_ACTIVE', 'value': 120, 'is_material': True, 'requires_restore': False},
                {'id': 'C2', 'name': 'van_loading', 'role': 'MATERIAL_ACTIVE', 'value': 86, 'is_material': True, 'requires_restore': False},
                {'id': 'C3', 'name': 'empty_pallet_reserve', 'role': 'DECOY_DISPENSABLE', 'value': 40, 'is_material': False, 'requires_restore': False},
            ],
            'required_intermediates': [120],
            'answer': 86,
            'edges': ['pallet_intake: 8 * 15 -> 120', 'van_deduction: 120 - 34 -> 86'],
            'consequence_step': None,
            'restore_targets': [],
            'decoy_components': ['C3'],
            'terminal_components': [],
        },
        {
            'id': 'L03',
            'name': 'Fleet Bus Transit',
            'prompt_core': 'A transit fleet operates 5 buses carrying 28 passengers each. At the central interchange, 45 passengers disembark. An express highway route has a toll cost of 50 credits but is not taken. How many passengers remain on the buses?',
            'components': [
                {'id': 'C1', 'name': 'bus_passenger_count', 'role': 'MATERIAL_ACTIVE', 'value': 140, 'is_material': True, 'requires_restore': False},
                {'id': 'C2', 'name': 'interchange_disembark', 'role': 'MATERIAL_ACTIVE', 'value': 95, 'is_material': True, 'requires_restore': False},
                {'id': 'C3', 'name': 'express_toll_cost', 'role': 'DECOY_DISPENSABLE', 'value': 50, 'is_material': False, 'requires_restore': False},
            ],
            'required_intermediates': [140],
            'answer': 95,
            'edges': ['bus_count: 5 * 28 -> 140', 'disembark_deduction: 140 - 45 -> 95'],
            'consequence_step': None,
            'restore_targets': [],
            'decoy_components': ['C3'],
            'terminal_components': [],
        },
        {
            'id': 'L04',
            'name': 'Hardware Bolt Assembly',
            'prompt_core': 'A technician opens 9 boxes containing 16 precision bolts each. 38 bolts are installed on an airframe assembly. A spare parts catalog lists an alternative titanium bolt grade priced at 25 credits. How many bolts remain in the boxes?',
            'components': [
                {'id': 'C1', 'name': 'box_bolt_inventory', 'role': 'MATERIAL_ACTIVE', 'value': 144, 'is_material': True, 'requires_restore': False},
                {'id': 'C2', 'name': 'airframe_installation', 'role': 'MATERIAL_ACTIVE', 'value': 106, 'is_material': True, 'requires_restore': False},
                {'id': 'C3', 'name': 'alternative_catalog_price', 'role': 'DECOY_DISPENSABLE', 'value': 25, 'is_material': False, 'requires_restore': False},
            ],
            'required_intermediates': [144],
            'answer': 106,
            'edges': ['bolt_inventory: 9 * 16 -> 144', 'installation_deduction: 144 - 38 -> 106'],
            'consequence_step': None,
            'restore_targets': [],
            'decoy_components': ['C3'],
            'terminal_components': [],
        },
        {
            'id': 'L05',
            'name': 'Agricultural Melon Crates',
            'prompt_core': 'A farm harvest collects 7 crates with 18 cantaloupes each. 29 cantaloupes are delivered to a farm shop. An unchilled rustic barn provides 50 square meters of floor space. How many cantaloupes remain in harvest inventory?',
            'components': [
                {'id': 'C1', 'name': 'crate_harvest', 'role': 'MATERIAL_ACTIVE', 'value': 126, 'is_material': True, 'requires_restore': False},
                {'id': 'C2', 'name': 'shop_delivery', 'role': 'MATERIAL_ACTIVE', 'value': 97, 'is_material': True, 'requires_restore': False},
                {'id': 'C3', 'name': 'barn_floor_space', 'role': 'DECOY_DISPENSABLE', 'value': 50, 'is_material': False, 'requires_restore': False},
            ],
            'required_intermediates': [126],
            'answer': 97,
            'edges': ['crate_harvest: 7 * 18 -> 126', 'delivery_deduction: 126 - 29 -> 97'],
            'consequence_step': None,
            'restore_targets': [],
            'decoy_components': ['C3'],
            'terminal_components': [],
        },
        {
            'id': 'L06',
            'name': 'Solar Microgrid Storage',
            'prompt_core': 'A solar microgrid has 4 inverter strings producing 35 kilowatt-hours each. An on-site battery absorbs 48 kilowatt-hours. A backup diesel generator has an uncoupled fuel tank of 60 liters. How many kilowatt-hours are fed directly to local facility loads?',
            'components': [
                {'id': 'C1', 'name': 'solar_inverter_generation', 'role': 'MATERIAL_ACTIVE', 'value': 140, 'is_material': True, 'requires_restore': False},
                {'id': 'C2', 'name': 'battery_absorption', 'role': 'MATERIAL_ACTIVE', 'value': 92, 'is_material': True, 'requires_restore': False},
                {'id': 'C3', 'name': 'diesel_fuel_tank', 'role': 'DECOY_DISPENSABLE', 'value': 60, 'is_material': False, 'requires_restore': False},
            ],
            'required_intermediates': [140],
            'answer': 92,
            'edges': ['solar_generation: 4 * 35 -> 140', 'battery_deduction: 140 - 48 -> 92'],
            'consequence_step': None,
            'restore_targets': [],
            'decoy_components': ['C3'],
            'terminal_components': [],
        },
        {
            'id': 'L07',
            'name': 'Publishing Book Shipment',
            'prompt_core': 'A bindery packages 8 cartons of 22 hardcover textbooks each. 53 textbooks are sent to university reviewers. A planned digital reprint edition has an estimated production schedule of 15 weeks. How many textbooks remain for retail distribution?',
            'components': [
                {'id': 'C1', 'name': 'bindery_carton_total', 'role': 'MATERIAL_ACTIVE', 'value': 176, 'is_material': True, 'requires_restore': False},
                {'id': 'C2', 'name': 'reviewer_distribution', 'role': 'MATERIAL_ACTIVE', 'value': 123, 'is_material': True, 'requires_restore': False},
                {'id': 'C3', 'name': 'digital_reprint_weeks', 'role': 'DECOY_DISPENSABLE', 'value': 15, 'is_material': False, 'requires_restore': False},
            ],
            'required_intermediates': [176],
            'answer': 123,
            'edges': ['carton_total: 8 * 22 -> 176', 'reviewer_deduction: 176 - 53 -> 123'],
            'consequence_step': None,
            'restore_targets': [],
            'decoy_components': ['C3'],
            'terminal_components': [],
        },
        {
            'id': 'L08',
            'name': 'Chemical Laboratory Reagents',
            'prompt_core': 'A testing laboratory prepares 6 vials containing 25 milliliters of test solution each. An assay procedure consumes 64 milliliters. A ventilation exhaust hood operates at 80 cubic feet per minute. How many milliliters of test solution remain?',
            'components': [
                {'id': 'C1', 'name': 'vial_total_volume', 'role': 'MATERIAL_ACTIVE', 'value': 150, 'is_material': True, 'requires_restore': False},
                {'id': 'C2', 'name': 'assay_consumption', 'role': 'MATERIAL_ACTIVE', 'value': 86, 'is_material': True, 'requires_restore': False},
                {'id': 'C3', 'name': 'exhaust_hood_rating', 'role': 'DECOY_DISPENSABLE', 'value': 80, 'is_material': False, 'requires_restore': False},
            ],
            'required_intermediates': [150],
            'answer': 86,
            'edges': ['vial_total: 6 * 25 -> 150', 'assay_deduction: 150 - 64 -> 86'],
            'consequence_step': None,
            'restore_targets': [],
            'decoy_components': ['C3'],
            'terminal_components': [],
        },
        {
            'id': 'L09',
            'name': 'School Notebook Supplies',
            'prompt_core': 'A school district receives 12 packs of 15 lined notebooks each. 67 notebooks are distributed to students on orientation day. An auxiliary supply closet has room for 45 pencil boxes. How many notebooks remain in storage?',
            'components': [
                {'id': 'C1', 'name': 'notebook_pack_total', 'role': 'MATERIAL_ACTIVE', 'value': 180, 'is_material': True, 'requires_restore': False},
                {'id': 'C2', 'name': 'orientation_distribution', 'role': 'MATERIAL_ACTIVE', 'value': 113, 'is_material': True, 'requires_restore': False},
                {'id': 'C3', 'name': 'closet_pencil_capacity', 'role': 'DECOY_DISPENSABLE', 'value': 45, 'is_material': False, 'requires_restore': False},
            ],
            'required_intermediates': [180],
            'answer': 113,
            'edges': ['pack_total: 12 * 15 -> 180', 'distribution_deduction: 180 - 67 -> 113'],
            'consequence_step': None,
            'restore_targets': [],
            'decoy_components': ['C3'],
            'terminal_components': [],
        },
        {
            'id': 'L10',
            'name': 'Ceramic Tile Installation',
            'prompt_core': 'A tile contractor delivers 5 cases of 32 floor tiles each. Masons install 71 tiles across a foyer floor. An unopened spare bag of dry grout weighs 25 kilograms. How many tiles remain in the cases?',
            'components': [
                {'id': 'C1', 'name': 'tile_case_total', 'role': 'MATERIAL_ACTIVE', 'value': 160, 'is_material': True, 'requires_restore': False},
                {'id': 'C2', 'name': 'foyer_installation', 'role': 'MATERIAL_ACTIVE', 'value': 89, 'is_material': True, 'requires_restore': False},
                {'id': 'C3', 'name': 'grout_bag_weight', 'role': 'DECOY_DISPENSABLE', 'value': 25, 'is_material': False, 'requires_restore': False},
            ],
            'required_intermediates': [160],
            'answer': 89,
            'edges': ['case_total: 5 * 32 -> 160', 'installation_deduction: 160 - 71 -> 89'],
            'consequence_step': None,
            'restore_targets': [],
            'decoy_components': ['C3'],
            'terminal_components': [],
        },
        {
            'id': 'L11',
            'name': 'Fruit Orchard Baskets',
            'prompt_core': 'An orchard packs 9 baskets containing 24 ripe peaches each. 85 peaches are sorted out for preserve making. An automated drip irrigation valve maintains a pressure of 40 psi. How many fresh peaches remain for market sale?',
            'components': [
                {'id': 'C1', 'name': 'basket_peach_total', 'role': 'MATERIAL_ACTIVE', 'value': 216, 'is_material': True, 'requires_restore': False},
                {'id': 'C2', 'name': 'preserve_sorting', 'role': 'MATERIAL_ACTIVE', 'value': 131, 'is_material': True, 'requires_restore': False},
                {'id': 'C3', 'name': 'drip_valve_psi', 'role': 'DECOY_DISPENSABLE', 'value': 40, 'is_material': False, 'requires_restore': False},
            ],
            'required_intermediates': [216],
            'answer': 131,
            'edges': ['basket_total: 9 * 24 -> 216', 'preserve_deduction: 216 - 85 -> 131'],
            'consequence_step': None,
            'restore_targets': [],
            'decoy_components': ['C3'],
            'terminal_components': [],
        },
        {
            'id': 'L12',
            'name': 'Network Fiber Conduit',
            'prompt_core': 'A data center installs fiber from 7 spools containing 26 meters of patch cable each. Technicians route 59 meters through ceiling raceways. A redundant uninterruptible power unit is rated at 750 watts. How many meters of cable remain on the spools?',
            'components': [
                {'id': 'C1', 'name': 'spool_cable_total', 'role': 'MATERIAL_ACTIVE', 'value': 182, 'is_material': True, 'requires_restore': False},
                {'id': 'C2', 'name': 'raceway_routing', 'role': 'MATERIAL_ACTIVE', 'value': 123, 'is_material': True, 'requires_restore': False},
                {'id': 'C3', 'name': 'ups_power_rating', 'role': 'DECOY_DISPENSABLE', 'value': 750, 'is_material': False, 'requires_restore': False},
            ],
            'required_intermediates': [182],
            'answer': 123,
            'edges': ['spool_total: 7 * 26 -> 182', 'routing_deduction: 182 - 59 -> 123'],
            'consequence_step': None,
            'restore_targets': [],
            'decoy_components': ['C3'],
            'terminal_components': [],
        },
    ]
    for spec in tier1_specs:
        spec['tier'] = 'local_short_horizon'
        families.append(spec)

    # TIER 2: Delayed-Dependency (D01-D12)
    tier2_specs = [
        {
            'id': 'D01',
            'name': 'Grain Terminal Inventory',
            'prompt_core': 'A grain terminal has an initial reserve of 45 tonnes of wheat in silo 1. An unused rail spur has track length for 12 hopper cars. During the morning, 6 trucks deliver 18 tonnes of wheat each into silo 1. In the afternoon, a bulk barge shipment takes 85 tonnes of wheat from silo 1. What is the final quantity of wheat remaining in silo 1?',
            'components': [
                {'id': 'C1', 'name': 'initial_silo_reserve', 'role': 'MATERIAL_DELAYED', 'value': 45, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'rail_spur_capacity', 'role': 'DECOY_DISPENSABLE', 'value': 12, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'morning_truck_deliveries', 'role': 'MATERIAL_ACTIVE', 'value': 108, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'total_wheat_available', 'role': 'MATERIAL_ACTIVE', 'value': 153, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'barge_shipment_remaining', 'role': 'MATERIAL_ACTIVE', 'value': 68, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [108, 153],
            'answer': 68,
            'edges': ['truck_product: 6 * 18 -> 108', 'reserve_accumulation: 45 + 108 -> 153', 'barge_deduction: 153 - 85 -> 68'],
            'consequence_step': 'Calculate total available wheat in silo 1 before barge deduction',
            'restore_targets': ['C1'],
            'decoy_components': ['C2'],
            'terminal_components': [],
        },
        {
            'id': 'D02',
            'name': 'Municipal Water Reservoir',
            'prompt_core': 'A municipal reservoir starts the week with a baseline volume of 60 megaliters. An emergency overflow spillway has a maximum discharge rating of 25 megaliters per hour. Over four days, 4 tributary streams each feed 16 megaliters into the reservoir. A treatment facility extracts 75 megaliters for municipal drinking water. What is the final volume of water in the reservoir?',
            'components': [
                {'id': 'C1', 'name': 'baseline_reservoir_volume', 'role': 'MATERIAL_DELAYED', 'value': 60, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'spillway_discharge_rating', 'role': 'DECOY_DISPENSABLE', 'value': 25, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'stream_inflow_total', 'role': 'MATERIAL_ACTIVE', 'value': 64, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'total_water_available', 'role': 'MATERIAL_ACTIVE', 'value': 124, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'treatment_extraction_remaining', 'role': 'MATERIAL_ACTIVE', 'value': 49, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [64, 124],
            'answer': 49,
            'edges': ['stream_product: 4 * 16 -> 64', 'reservoir_accumulation: 60 + 64 -> 124', 'treatment_deduction: 124 - 75 -> 49'],
            'consequence_step': 'Calculate total available water volume before municipal treatment extraction',
            'restore_targets': ['C1'],
            'decoy_components': ['C2'],
            'terminal_components': [],
        },
        {
            'id': 'D03',
            'name': 'Fuel Depot Storage',
            'prompt_core': 'A logistics depot maintains an initial bunker reserve of 55 kiloliters of diesel fuel. An unassigned spare road tanker has a tank capacity of 18 kiloliters. A supply train discharges 7 tank wagons holding 14 kiloliters each into the bunker. Depot pumps dispense 82 kiloliters to service fleet trucks. How many kiloliters of diesel fuel remain in the bunker?',
            'components': [
                {'id': 'C1', 'name': 'initial_bunker_reserve', 'role': 'MATERIAL_DELAYED', 'value': 55, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'spare_tanker_capacity', 'role': 'DECOY_DISPENSABLE', 'value': 18, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'wagon_discharge_total', 'role': 'MATERIAL_ACTIVE', 'value': 98, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'total_diesel_available', 'role': 'MATERIAL_ACTIVE', 'value': 153, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'fleet_dispense_remaining', 'role': 'MATERIAL_ACTIVE', 'value': 71, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [98, 153],
            'answer': 71,
            'edges': ['wagon_product: 7 * 14 -> 98', 'bunker_accumulation: 55 + 98 -> 153', 'fleet_deduction: 153 - 82 -> 71'],
            'consequence_step': 'Calculate total available diesel in bunker before fleet truck dispensing',
            'restore_targets': ['C1'],
            'decoy_components': ['C2'],
            'terminal_components': [],
        },
        {
            'id': 'D04',
            'name': 'Hospital Blood Plasma Bank',
            'prompt_core': 'A regional hospital blood bank holds an initial baseline stock of 40 units of type O plasma. A refrigerated emergency backup cabinet has 30 empty shelves. Five donor drives collect 15 units of type O plasma each and deposit them in the blood bank. Hospital surgical rooms request and use 68 units. How many units of type O plasma remain in the blood bank?',
            'components': [
                {'id': 'C1', 'name': 'baseline_plasma_stock', 'role': 'MATERIAL_DELAYED', 'value': 40, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'backup_cabinet_shelves', 'role': 'DECOY_DISPENSABLE', 'value': 30, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'donor_drive_total', 'role': 'MATERIAL_ACTIVE', 'value': 75, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'total_plasma_available', 'role': 'MATERIAL_ACTIVE', 'value': 115, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'surgical_usage_remaining', 'role': 'MATERIAL_ACTIVE', 'value': 47, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [75, 115],
            'answer': 47,
            'edges': ['donor_product: 5 * 15 -> 75', 'plasma_accumulation: 40 + 75 -> 115', 'surgical_deduction: 115 - 68 -> 47'],
            'consequence_step': 'Calculate total plasma available before surgical room deduction',
            'restore_targets': ['C1'],
            'decoy_components': ['C2'],
            'terminal_components': [],
        },
        {
            'id': 'D05',
            'name': 'Port Container Yard Staging',
            'prompt_core': 'A maritime container yard has an initial staging inventory of 50 empty containers in Zone A. A standby mobile gantry crane has a lifting capacity of 35 metric tonnes. Eight drayage trucks deliver 12 empty containers each into Zone A. A container ship loads 88 empty containers from Zone A onto its deck. How many empty containers remain in Zone A?',
            'components': [
                {'id': 'C1', 'name': 'initial_zone_a_inventory', 'role': 'MATERIAL_DELAYED', 'value': 50, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'gantry_crane_capacity', 'role': 'DECOY_DISPENSABLE', 'value': 35, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'truck_delivery_total', 'role': 'MATERIAL_ACTIVE', 'value': 96, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'total_containers_available', 'role': 'MATERIAL_ACTIVE', 'value': 146, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'ship_loading_remaining', 'role': 'MATERIAL_ACTIVE', 'value': 58, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [96, 146],
            'answer': 58,
            'edges': ['truck_product: 8 * 12 -> 96', 'container_accumulation: 50 + 96 -> 146', 'ship_deduction: 146 - 88 -> 58'],
            'consequence_step': 'Calculate total empty containers in Zone A before ship loading',
            'restore_targets': ['C1'],
            'decoy_components': ['C2'],
            'terminal_components': [],
        },
        {
            'id': 'D06',
            'name': 'Horticultural Nursery Seedlings',
            'prompt_core': 'A commercial greenhouse holds an initial nursery batch of 35 heirloom tomato seedlings. An adjacent unheated propagation bench provides 45 square meters of surface area. Staff germinate 6 new plug trays containing 17 tomato seedlings each and transfer them to the greenhouse. A landscaping company purchases 79 seedlings. How many tomato seedlings remain in the greenhouse?',
            'components': [
                {'id': 'C1', 'name': 'initial_seedling_batch', 'role': 'MATERIAL_DELAYED', 'value': 35, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'propagation_bench_area', 'role': 'DECOY_DISPENSABLE', 'value': 45, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'germination_tray_total', 'role': 'MATERIAL_ACTIVE', 'value': 102, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'total_seedlings_available', 'role': 'MATERIAL_ACTIVE', 'value': 137, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'purchase_remaining', 'role': 'MATERIAL_ACTIVE', 'value': 58, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [102, 137],
            'answer': 58,
            'edges': ['tray_product: 6 * 17 -> 102', 'seedling_accumulation: 35 + 102 -> 137', 'purchase_deduction: 137 - 79 -> 58'],
            'consequence_step': 'Calculate total seedlings available before contractor purchase',
            'restore_targets': ['C1'],
            'decoy_components': ['C2'],
            'terminal_components': [],
        },
        {
            'id': 'D07',
            'name': 'Construction Rebar Inventory',
            'prompt_core': 'A bridge construction site starts the shift with an on-site reserve of 65 bundles of rebar. A secondary concrete transit mixer has a drum capacity of 9 cubic meters. Five flatbed deliveries arrive, each carrying 14 bundles of rebar. Ironworkers place and tie 86 bundles of rebar into the pier footings. How many bundles of rebar remain on-site?',
            'components': [
                {'id': 'C1', 'name': 'initial_rebar_reserve', 'role': 'MATERIAL_DELAYED', 'value': 65, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'mixer_drum_capacity', 'role': 'DECOY_DISPENSABLE', 'value': 9, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'flatbed_delivery_total', 'role': 'MATERIAL_ACTIVE', 'value': 70, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'total_rebar_available', 'role': 'MATERIAL_ACTIVE', 'value': 135, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'pier_installation_remaining', 'role': 'MATERIAL_ACTIVE', 'value': 49, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [70, 135],
            'answer': 49,
            'edges': ['flatbed_product: 5 * 14 -> 70', 'rebar_accumulation: 65 + 70 -> 135', 'pier_deduction: 135 - 86 -> 49'],
            'consequence_step': 'Calculate total rebar bundles on-site before pier tie-in',
            'restore_targets': ['C1'],
            'decoy_components': ['C2'],
            'terminal_components': [],
        },
        {
            'id': 'D08',
            'name': 'Bicycle Transit Hub Station',
            'prompt_core': 'A central metro station begins morning operations with 48 bicycles locked in docking stations. An unstriped auxiliary curb lane has space for 20 mopeds. A service van replenishes the station by unloading 4 racks holding 16 bicycles each. During the morning rush hour, 73 bicycles are checked out by commuters. How many bicycles remain docked at the station?',
            'components': [
                {'id': 'C1', 'name': 'initial_docked_bicycles', 'role': 'MATERIAL_DELAYED', 'value': 48, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'moped_lane_space', 'role': 'DECOY_DISPENSABLE', 'value': 20, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'van_replenish_total', 'role': 'MATERIAL_ACTIVE', 'value': 64, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'total_bicycles_available', 'role': 'MATERIAL_ACTIVE', 'value': 112, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'commuter_checkout_remaining', 'role': 'MATERIAL_ACTIVE', 'value': 39, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [64, 112],
            'answer': 39,
            'edges': ['van_product: 4 * 16 -> 64', 'bicycle_accumulation: 48 + 64 -> 112', 'commuter_deduction: 112 - 73 -> 39'],
            'consequence_step': 'Calculate total bicycles docked before commuter checkout',
            'restore_targets': ['C1'],
            'decoy_components': ['C2'],
            'terminal_components': [],
        },
        {
            'id': 'D09',
            'name': 'Dairy Processing Tank',
            'prompt_core': 'A dairy processing room holds an initial base volume of 75 liters of whole milk in its central tank. A pasture drainage channel measures 250 meters in length. Morning milking across 7 dairy stanchions yields 19 liters each into the central tank. The creamery pasteurizes and bottles 128 liters for distribution. How many liters of milk remain in the central tank?',
            'components': [
                {'id': 'C1', 'name': 'initial_milk_volume', 'role': 'MATERIAL_DELAYED', 'value': 75, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'drainage_channel_length', 'role': 'DECOY_DISPENSABLE', 'value': 250, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'milking_yield_total', 'role': 'MATERIAL_ACTIVE', 'value': 133, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'total_milk_available', 'role': 'MATERIAL_ACTIVE', 'value': 208, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'bottling_remaining', 'role': 'MATERIAL_ACTIVE', 'value': 80, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [133, 208],
            'answer': 80,
            'edges': ['milking_product: 7 * 19 -> 133', 'milk_accumulation: 75 + 133 -> 208', 'bottling_deduction: 208 - 128 -> 80'],
            'consequence_step': 'Calculate total milk in central tank before bottling deduction',
            'restore_targets': ['C1'],
            'decoy_components': ['C2'],
            'terminal_components': [],
        },
        {
            'id': 'D10',
            'name': 'Aerospace Rivet Inventory',
            'prompt_core': 'An aircraft repair hangar stocks a baseline tray of 80 structural titanium rivets. An auxiliary pneumatic workshop compressor is rated at 120 psi. A supplier delivers 6 sealed packets containing 22 titanium rivets each. Assembly mechanics install 145 rivets during an engine cowl replacement. How many titanium rivets remain in hangar stock?',
            'components': [
                {'id': 'C1', 'name': 'baseline_rivet_tray', 'role': 'MATERIAL_DELAYED', 'value': 80, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'compressor_psi_rating', 'role': 'DECOY_DISPENSABLE', 'value': 120, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'packet_delivery_total', 'role': 'MATERIAL_ACTIVE', 'value': 132, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'total_rivets_available', 'role': 'MATERIAL_ACTIVE', 'value': 212, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'cowl_installation_remaining', 'role': 'MATERIAL_ACTIVE', 'value': 67, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [132, 212],
            'answer': 67,
            'edges': ['packet_product: 6 * 22 -> 132', 'rivet_accumulation: 80 + 132 -> 212', 'cowl_deduction: 212 - 145 -> 67'],
            'consequence_step': 'Calculate total titanium rivets available before cowl replacement',
            'restore_targets': ['C1'],
            'decoy_components': ['C2'],
            'terminal_components': [],
        },
        {
            'id': 'D11',
            'name': 'Brewery Finished Kegs',
            'prompt_core': 'A craft brewery cold room holds an initial inventory of 52 finished kegs. An idle grain roller mill has an operating speed of 1800 rpm. The packaging line completes and chills 5 pallets holding 15 kegs each. A regional distributor loads 84 kegs onto its refrigerated truck. How many finished kegs remain in the cold room?',
            'components': [
                {'id': 'C1', 'name': 'initial_cold_room_kegs', 'role': 'MATERIAL_DELAYED', 'value': 52, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'roller_mill_speed', 'role': 'DECOY_DISPENSABLE', 'value': 1800, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'packaging_pallet_total', 'role': 'MATERIAL_ACTIVE', 'value': 75, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'total_kegs_available', 'role': 'MATERIAL_ACTIVE', 'value': 127, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'distributor_loading_remaining', 'role': 'MATERIAL_ACTIVE', 'value': 43, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [75, 127],
            'answer': 43,
            'edges': ['pallet_product: 5 * 15 -> 75', 'keg_accumulation: 52 + 75 -> 127', 'distributor_deduction: 127 - 84 -> 43'],
            'consequence_step': 'Calculate total kegs available before distributor truck loading',
            'restore_targets': ['C1'],
            'decoy_components': ['C2'],
            'terminal_components': [],
        },
        {
            'id': 'D12',
            'name': 'Industrial Energy Battery Storage',
            'prompt_core': 'An energy storage facility starts the day with an initial battery state of 90 kilowatt-hours. A non-operational cooling ventilation fan has an impeller diameter of 60 centimeters. Solar arrays feed 8 power converters producing 18 kilowatt-hours each into the battery bank. An evening industrial processing cycle draws 165 kilowatt-hours. How many kilowatt-hours remain in the battery bank?',
            'components': [
                {'id': 'C1', 'name': 'initial_battery_kwh', 'role': 'MATERIAL_DELAYED', 'value': 90, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'fan_impeller_diameter', 'role': 'DECOY_DISPENSABLE', 'value': 60, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'converter_inflow_total', 'role': 'MATERIAL_ACTIVE', 'value': 144, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'total_kwh_available', 'role': 'MATERIAL_ACTIVE', 'value': 234, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'industrial_draw_remaining', 'role': 'MATERIAL_ACTIVE', 'value': 69, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [144, 234],
            'answer': 69,
            'edges': ['converter_product: 8 * 18 -> 144', 'battery_accumulation: 90 + 144 -> 234', 'industrial_deduction: 234 - 165 -> 69'],
            'consequence_step': 'Calculate total kilowatt-hours available in battery bank before industrial draw',
            'restore_targets': ['C1'],
            'decoy_components': ['C2'],
            'terminal_components': [],
        },
    ]
    for spec in tier2_specs:
        spec['tier'] = 'delayed_dependency'
        families.append(spec)

    # TIER 3: Reactivation (R01-R12)
    tier3_specs = [
        {
            'id': 'R01',
            'name': 'Cable Assembly Production',
            'prompt_core': 'In Phase 1, Production Line 1 produces 4 bundles of 6 cables each. Simultaneously, an intake audit writes off 2 groups of 8 cables from a separate 90-cable scrap bin, permanently closing the scrap log. In Phase 2, Production Line 2 processes 5 boxes of 9 cables each, and dispatches 28 of those cables to quality control. In Phase 3, a priority rush order requires exactly 3 times the cable quantity produced by Line 1, plus all remaining cables from Line 2. How many cables are delivered for the rush order?',
            'components': [
                {'id': 'C1', 'name': 'line1_bundle_production', 'role': 'MATERIAL_REACTIVATED', 'value': 24, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'scrap_audit_writeoff', 'role': 'RESOLVED_TERMINAL', 'value': 74, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'line2_box_processing', 'role': 'MATERIAL_ACTIVE', 'value': 45, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'line2_remaining_cables', 'role': 'MATERIAL_ACTIVE', 'value': 17, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'line1_rush_expansion', 'role': 'MATERIAL_ACTIVE', 'value': 72, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [24, 45, 17, 72],
            'answer': 89,
            'edges': ['line1_product: 4 * 6 -> 24', 'scrap_terminal: 90 - (2 * 8) -> 74', 'line2_product: 5 * 9 -> 45', 'line2_net: 45 - 28 -> 17', 'rush_line1_factor: 3 * 24 -> 72', 'rush_total: 72 + 17 -> 89'],
            'consequence_step': 'Calculate Phase 3 rush order requiring 3 times Line 1 production plus Line 2 remainder',
            'restore_targets': ['C1'],
            'decoy_components': [],
            'terminal_components': ['C2'],
        },
        {
            'id': 'R02',
            'name': 'Industrial Filter Packaging',
            'prompt_core': 'In Phase 1, Pack Station A packs 3 cartons of 8 hydraulic filters each. Meanwhile, an intake audit writes off 3 packs of 7 gaskets from an 80-gasket reserve bin, permanently closing the gasket log. In Phase 2, Pack Station B packs 6 cartons of 7 hydraulic filters each, and ships 25 of those filters to an assembly floor. In Phase 3, an expedited contract demands 4 times the filter quantity packed by Station A, plus all remaining filters from Station B. How many filters are provided for the expedited contract?',
            'components': [
                {'id': 'C1', 'name': 'station_a_pack_quantity', 'role': 'MATERIAL_REACTIVATED', 'value': 24, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'gasket_audit_writeoff', 'role': 'RESOLVED_TERMINAL', 'value': 59, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'station_b_carton_pack', 'role': 'MATERIAL_ACTIVE', 'value': 42, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'station_b_remaining_filters', 'role': 'MATERIAL_ACTIVE', 'value': 17, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'station_a_contract_expansion', 'role': 'MATERIAL_ACTIVE', 'value': 96, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [24, 42, 17, 96],
            'answer': 113,
            'edges': ['station_a_product: 3 * 8 -> 24', 'gasket_terminal: 80 - (3 * 7) -> 59', 'station_b_product: 6 * 7 -> 42', 'station_b_net: 42 - 25 -> 17', 'contract_station_a_factor: 4 * 24 -> 96', 'contract_total: 96 + 17 -> 113'],
            'consequence_step': 'Calculate Phase 3 expedited contract requiring 4 times Station A quantity plus Station B remainder',
            'restore_targets': ['C1'],
            'decoy_components': [],
            'terminal_components': ['C2'],
        },
        {
            'id': 'R03',
            'name': 'Machining Bracket Fabrication',
            'prompt_core': 'In Phase 1, Mill 1 machines 5 trays of 7 steel brackets each. Meanwhile, tool crib staff deduct 4 sets of 6 fasteners from a 100-fastener auxiliary bin, permanently archiving the fastener ticket. In Phase 2, Mill 2 machines 7 trays of 6 steel brackets each, and delivers 29 of those brackets to finishing. In Phase 3, final assembly requires 2 times the bracket output of Mill 1, plus all remaining brackets from Mill 2. How many brackets are sent to final assembly?',
            'components': [
                {'id': 'C1', 'name': 'mill1_tray_output', 'role': 'MATERIAL_REACTIVATED', 'value': 35, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'fastener_ticket_deduction', 'role': 'RESOLVED_TERMINAL', 'value': 76, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'mill2_tray_machining', 'role': 'MATERIAL_ACTIVE', 'value': 42, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'mill2_remaining_brackets', 'role': 'MATERIAL_ACTIVE', 'value': 13, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'mill1_assembly_expansion', 'role': 'MATERIAL_ACTIVE', 'value': 70, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [35, 42, 13, 70],
            'answer': 83,
            'edges': ['mill1_product: 5 * 7 -> 35', 'fastener_terminal: 100 - (4 * 6) -> 76', 'mill2_product: 7 * 6 -> 42', 'mill2_net: 42 - 29 -> 13', 'assembly_mill1_factor: 2 * 35 -> 70', 'assembly_total: 70 + 13 -> 83'],
            'consequence_step': 'Calculate Phase 3 assembly requirement requiring 2 times Mill 1 output plus Mill 2 remainder',
            'restore_targets': ['C1'],
            'decoy_components': [],
            'terminal_components': ['C2'],
        },
        {
            'id': 'R04',
            'name': 'Precision Bearing Sleevings',
            'prompt_core': 'In Phase 1, Lathe Station 1 packs 6 sleeves of 5 roller bearings each. Concurrently, maintenance staff withdraw 3 kits of 9 washers from a 95-washer drawer, permanently closing the withdrawal form. In Phase 2, Lathe Station 2 packs 4 sleeves of 11 roller bearings each, and transfers 26 of those bearings to inspection. In Phase 3, an overseas client orders 3 times the bearing batch produced by Station 1, plus all remaining bearings from Station 2. How many bearings are dispatched to the overseas client?',
            'components': [
                {'id': 'C1', 'name': 'station1_sleeve_batch', 'role': 'MATERIAL_REACTIVATED', 'value': 30, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'washer_withdrawal_close', 'role': 'RESOLVED_TERMINAL', 'value': 68, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'station2_sleeve_packing', 'role': 'MATERIAL_ACTIVE', 'value': 44, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'station2_remaining_bearings', 'role': 'MATERIAL_ACTIVE', 'value': 18, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'station1_client_expansion', 'role': 'MATERIAL_ACTIVE', 'value': 90, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [30, 44, 18, 90],
            'answer': 108,
            'edges': ['station1_product: 6 * 5 -> 30', 'washer_terminal: 95 - (3 * 9) -> 68', 'station2_product: 4 * 11 -> 44', 'station2_net: 44 - 26 -> 18', 'client_station1_factor: 3 * 30 -> 90', 'client_total: 90 + 18 -> 108'],
            'consequence_step': 'Calculate Phase 3 overseas dispatch requiring 3 times Station 1 batch plus Station 2 remainder',
            'restore_targets': ['C1'],
            'decoy_components': [],
            'terminal_components': ['C2'],
        },
        {
            'id': 'R05',
            'name': 'Mounting Clamp Workshop',
            'prompt_core': 'In Phase 1, Workshop Alpha fabricates 4 packs of 8 pipe clamps each. Concurrently, electrical maintenance replaces 5 fixtures using 4 fuses each from a 70-fuse parts rack, permanently completing the repair log. In Phase 2, Workshop Beta fabricates 5 packs of 9 pipe clamps each, and issues 31 of those clamps to field teams. In Phase 3, a plumbing contractor purchases 2 times the clamp fabrication of Workshop Alpha, plus all remaining clamps from Workshop Beta. How many clamps does the contractor receive?',
            'components': [
                {'id': 'C1', 'name': 'alpha_clamp_pack_output', 'role': 'MATERIAL_REACTIVATED', 'value': 32, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'fuse_replacement_terminal', 'role': 'RESOLVED_TERMINAL', 'value': 50, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'beta_clamp_pack_fabrication', 'role': 'MATERIAL_ACTIVE', 'value': 45, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'beta_remaining_clamps', 'role': 'MATERIAL_ACTIVE', 'value': 14, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'alpha_contractor_expansion', 'role': 'MATERIAL_ACTIVE', 'value': 64, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [32, 45, 14, 64],
            'answer': 78,
            'edges': ['alpha_product: 4 * 8 -> 32', 'fuse_terminal: 70 - (5 * 4) -> 50', 'beta_product: 5 * 9 -> 45', 'beta_net: 45 - 31 -> 14', 'contractor_alpha_factor: 2 * 32 -> 64', 'contractor_total: 64 + 14 -> 78'],
            'consequence_step': 'Calculate Phase 3 contractor order requiring 2 times Workshop Alpha fabrication plus Workshop Beta remainder',
            'restore_targets': ['C1'],
            'decoy_components': [],
            'terminal_components': ['C2'],
        },
        {
            'id': 'R06',
            'name': 'Pneumatic Valve Assembly',
            'prompt_core': 'In Phase 1, Assembly Bay 1 builds 3 cases of 9 brass valves each. At the same time, a tool calibration check scraps 2 sets of 12 worn drill inserts from a 110-insert locker, permanently sealing the calibration sheet. In Phase 2, Assembly Bay 2 builds 7 cases of 7 brass valves each, and sends 34 of those valves to leak testing. In Phase 3, an installation project requires 3 times the valve output of Bay 1, plus all remaining valves from Bay 2. How many valves are supplied to the installation project?',
            'components': [
                {'id': 'C1', 'name': 'bay1_case_valve_output', 'role': 'MATERIAL_REACTIVATED', 'value': 27, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'drill_insert_scrap_seal', 'role': 'RESOLVED_TERMINAL', 'value': 86, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'bay2_case_valve_building', 'role': 'MATERIAL_ACTIVE', 'value': 49, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'bay2_remaining_valves', 'role': 'MATERIAL_ACTIVE', 'value': 15, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'bay1_project_expansion', 'role': 'MATERIAL_ACTIVE', 'value': 81, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [27, 49, 15, 81],
            'answer': 96,
            'edges': ['bay1_product: 3 * 9 -> 27', 'insert_terminal: 110 - (2 * 12) -> 86', 'bay2_product: 7 * 7 -> 49', 'bay2_net: 49 - 34 -> 15', 'project_bay1_factor: 3 * 27 -> 81', 'project_total: 81 + 15 -> 96'],
            'consequence_step': 'Calculate Phase 3 installation supply requiring 3 times Bay 1 output plus Bay 2 remainder',
            'restore_targets': ['C1'],
            'decoy_components': [],
            'terminal_components': ['C2'],
        },
        {
            'id': 'R07',
            'name': 'Optical Sensor Manufacturing',
            'prompt_core': 'In Phase 1, Plant East manufactures 6 cartons of 6 infrared sensors each. Meanwhile, plant security retires 4 batches of 5 obsolete access keycards from a 60-keycard depot box, permanently locking the security ledger. In Phase 2, Plant West manufactures 8 cartons of 5 infrared sensors each, and routes 27 of those sensors to spectral calibration. In Phase 3, an automation vendor purchases 2 times the sensor batch produced by Plant East, plus all remaining sensors from Plant West. How many sensors are shipped to the vendor?',
            'components': [
                {'id': 'C1', 'name': 'east_carton_sensor_batch', 'role': 'MATERIAL_REACTIVATED', 'value': 36, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'keycard_retirement_lock', 'role': 'RESOLVED_TERMINAL', 'value': 40, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'west_carton_sensor_output', 'role': 'MATERIAL_ACTIVE', 'value': 40, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'west_remaining_sensors', 'role': 'MATERIAL_ACTIVE', 'value': 13, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'east_vendor_expansion', 'role': 'MATERIAL_ACTIVE', 'value': 72, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [36, 40, 13, 72],
            'answer': 85,
            'edges': ['east_product: 6 * 6 -> 36', 'keycard_terminal: 60 - (4 * 5) -> 40', 'west_product: 8 * 5 -> 40', 'west_net: 40 - 27 -> 13', 'vendor_east_factor: 2 * 36 -> 72', 'vendor_total: 72 + 13 -> 85'],
            'consequence_step': 'Calculate Phase 3 vendor shipment requiring 2 times Plant East batch plus Plant West remainder',
            'restore_targets': ['C1'],
            'decoy_components': [],
            'terminal_components': ['C2'],
        },
        {
            'id': 'R08',
            'name': 'Molded Conduit Fittings',
            'prompt_core': 'In Phase 1, Molding Line A casts 5 crates of 8 conduit fittings each. Meanwhile, quality assurance rejects 3 batches of 6 damaged connector collars from an 85-collar staging crate, permanently filing the disposition ticket. In Phase 2, Molding Line B casts 6 crates of 7 conduit fittings each, and ships 26 of those fittings to a regional distributor. In Phase 3, an infrastructure project orders 2 times the fitting quantity produced by Line A, plus all remaining fittings from Line B. How many fittings are fulfilled for the infrastructure project?',
            'components': [
                {'id': 'C1', 'name': 'line_a_crate_fitting_total', 'role': 'MATERIAL_REACTIVATED', 'value': 40, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'collar_disposition_filing', 'role': 'RESOLVED_TERMINAL', 'value': 67, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'line_b_crate_casting', 'role': 'MATERIAL_ACTIVE', 'value': 42, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'line_b_remaining_fittings', 'role': 'MATERIAL_ACTIVE', 'value': 16, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'line_a_project_expansion', 'role': 'MATERIAL_ACTIVE', 'value': 80, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [40, 42, 16, 80],
            'answer': 96,
            'edges': ['line_a_product: 5 * 8 -> 40', 'collar_terminal: 85 - (3 * 6) -> 67', 'line_b_product: 6 * 7 -> 42', 'line_b_net: 42 - 26 -> 16', 'project_line_a_factor: 2 * 40 -> 80', 'project_total: 80 + 16 -> 96'],
            'consequence_step': 'Calculate Phase 3 infrastructure order requiring 2 times Line A quantity plus Line B remainder',
            'restore_targets': ['C1'],
            'decoy_components': [],
            'terminal_components': ['C2'],
        },
        {
            'id': 'R09',
            'name': 'Wiring Harness Preparation',
            'prompt_core': 'In Phase 1, Prep Crew 1 bundles 4 sets of 9 engine wiring harnesses each. Concurrently, yard maintenance scraps 2 groups of 7 damaged hand-truck wheels from a 50-wheel maintenance bay, permanently signing off the scrap manifest. In Phase 2, Prep Crew 2 bundles 7 sets of 6 engine wiring harnesses each, and installs 25 of those harnesses into chassis frames. In Phase 3, a defense contractor orders 3 times the harness quantity prepared by Crew 1, plus all remaining harnesses from Crew 2. How many harnesses are delivered to the defense contractor?',
            'components': [
                {'id': 'C1', 'name': 'crew1_harness_bundle_total', 'role': 'MATERIAL_REACTIVATED', 'value': 36, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'wheel_scrap_manifest_signoff', 'role': 'RESOLVED_TERMINAL', 'value': 36, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'crew2_harness_bundling', 'role': 'MATERIAL_ACTIVE', 'value': 42, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'crew2_remaining_harnesses', 'role': 'MATERIAL_ACTIVE', 'value': 17, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'crew1_contractor_expansion', 'role': 'MATERIAL_ACTIVE', 'value': 108, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [36, 42, 17, 108],
            'answer': 125,
            'edges': ['crew1_product: 4 * 9 -> 36', 'wheel_terminal: 50 - (2 * 7) -> 36', 'crew2_product: 7 * 6 -> 42', 'crew2_net: 42 - 25 -> 17', 'contractor_crew1_factor: 3 * 36 -> 108', 'contractor_total: 108 + 17 -> 125'],
            'consequence_step': 'Calculate Phase 3 defense delivery requiring 3 times Crew 1 quantity plus Crew 2 remainder',
            'restore_targets': ['C1'],
            'decoy_components': [],
            'terminal_components': ['C2'],
        },
        {
            'id': 'R10',
            'name': 'Bronze Bushing Casting',
            'prompt_core': 'In Phase 1, Foundry Unit 1 casts 4 lots of 7 bronze bushings each. Concurrently, machinery maintenance expends 4 packs of 8 lubrication seals from an 80-seal inventory drawer, permanently archiving the work order. In Phase 2, Foundry Unit 2 casts 5 lots of 9 bronze bushings each, and delivers 29 of those bushings to gearhead assembly. In Phase 3, a pump manufacturer requests 3 times the bushing quantity cast by Unit 1, plus all remaining bushings from Unit 2. How many bushings are supplied to the pump manufacturer?',
            'components': [
                {'id': 'C1', 'name': 'unit1_bushing_lot_total', 'role': 'MATERIAL_REACTIVATED', 'value': 28, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'lubrication_seal_archive', 'role': 'RESOLVED_TERMINAL', 'value': 48, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'unit2_bushing_lot_casting', 'role': 'MATERIAL_ACTIVE', 'value': 45, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'unit2_remaining_bushings', 'role': 'MATERIAL_ACTIVE', 'value': 16, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'unit1_pump_expansion', 'role': 'MATERIAL_ACTIVE', 'value': 84, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [28, 45, 16, 84],
            'answer': 100,
            'edges': ['unit1_product: 4 * 7 -> 28', 'seal_terminal: 80 - (4 * 8) -> 48', 'unit2_product: 5 * 9 -> 45', 'unit2_net: 45 - 29 -> 16', 'pump_unit1_factor: 3 * 28 -> 84', 'pump_total: 84 + 16 -> 100'],
            'consequence_step': 'Calculate Phase 3 pump order requiring 3 times Unit 1 quantity plus Unit 2 remainder',
            'restore_targets': ['C1'],
            'decoy_components': [],
            'terminal_components': ['C2'],
        },
        {
            'id': 'R11',
            'name': 'Jumper Wire Loom Assembly',
            'prompt_core': 'In Phase 1, Workcell 1 solders 6 rolls containing 7 jumper wire leads each. Simultaneously, electrical stores write off 3 boxes of 9 defective fuses from a 90-fuse auxiliary cabinet, permanently closing the disposal log. In Phase 2, Workcell 2 solders 4 rolls containing 12 jumper wire leads each, and transfers 31 of those leads to bench test fixtures. In Phase 3, an instrument rack installer orders 2 times the lead quantity soldered by Workcell 1, plus all remaining leads from Workcell 2. How many leads are shipped to the installer?',
            'components': [
                {'id': 'C1', 'name': 'workcell1_lead_roll_total', 'role': 'MATERIAL_REACTIVATED', 'value': 42, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'fuse_disposal_close', 'role': 'RESOLVED_TERMINAL', 'value': 63, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'workcell2_lead_roll_soldering', 'role': 'MATERIAL_ACTIVE', 'value': 48, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'workcell2_remaining_leads', 'role': 'MATERIAL_ACTIVE', 'value': 17, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'workcell1_installer_expansion', 'role': 'MATERIAL_ACTIVE', 'value': 84, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [42, 48, 17, 84],
            'answer': 101,
            'edges': ['workcell1_product: 6 * 7 -> 42', 'fuse_terminal: 90 - (3 * 9) -> 63', 'workcell2_product: 4 * 12 -> 48', 'workcell2_net: 48 - 31 -> 17', 'installer_workcell1_factor: 2 * 42 -> 84', 'installer_total: 84 + 17 -> 101'],
            'consequence_step': 'Calculate Phase 3 installer order requiring 2 times Workcell 1 quantity plus Workcell 2 remainder',
            'restore_targets': ['C1'],
            'decoy_components': [],
            'terminal_components': ['C2'],
        },
        {
            'id': 'R12',
            'name': 'Manifold Gasket Cutting',
            'prompt_core': 'In Phase 1, Press 1 stamps 5 packages of 9 high-pressure gaskets each. Concurrently, scrap recovery sorts out 2 bins of 11 distorted bracket stampings from a 75-bracket recycle hopper, permanently finalizing the scrap manifest. In Phase 2, Press 2 stamps 7 packages of 7 high-pressure gaskets each, and supplies 33 of those gaskets to engine testing. In Phase 3, a pipeline compressor plant requests 2 times the gasket output stamped by Press 1, plus all remaining gaskets from Press 2. How many gaskets are dispatched to the compressor plant?',
            'components': [
                {'id': 'C1', 'name': 'press1_package_gasket_total', 'role': 'MATERIAL_REACTIVATED', 'value': 45, 'is_material': True, 'requires_restore': True},
                {'id': 'C2', 'name': 'bracket_scrap_manifest_final', 'role': 'RESOLVED_TERMINAL', 'value': 53, 'is_material': False, 'requires_restore': False},
                {'id': 'C3', 'name': 'press2_package_gasket_stamping', 'role': 'MATERIAL_ACTIVE', 'value': 49, 'is_material': True, 'requires_restore': False},
                {'id': 'C4', 'name': 'press2_remaining_gaskets', 'role': 'MATERIAL_ACTIVE', 'value': 16, 'is_material': True, 'requires_restore': False},
                {'id': 'C5', 'name': 'press1_compressor_expansion', 'role': 'MATERIAL_ACTIVE', 'value': 90, 'is_material': True, 'requires_restore': False},
            ],
            'required_intermediates': [45, 49, 16, 90],
            'answer': 106,
            'edges': ['press1_product: 5 * 9 -> 45', 'bracket_terminal: 75 - (2 * 11) -> 53', 'press2_product: 7 * 7 -> 49', 'press2_net: 49 - 33 -> 16', 'compressor_press1_factor: 2 * 45 -> 90', 'compressor_total: 90 + 16 -> 106'],
            'consequence_step': 'Calculate Phase 3 compressor plant dispatch requiring 2 times Press 1 output plus Press 2 remainder',
            'restore_targets': ['C1'],
            'decoy_components': [],
            'terminal_components': ['C2'],
        },
    ]
    for spec in tier3_specs:
        spec['tier'] = 'reactivation'
        families.append(spec)

    return families

def generate_all():
    repo_root = Path('/home/njaal/all-repos/research')
    runs_dir = repo_root / 'runs' / 'NJAL-R01'
    runs_dir.mkdir(parents=True, exist_ok=True)

    families = create_task_definitions()
    assert len(families) == 36, f'Expected 36 families, got {len(families)}'

    task_set = []
    answer_key = []
    dep_map = {
        'protocol': 'NJAL-R01',
        'version': '0.1',
        'frozen_at': '2026-09-12',
        'primary_invariants': [
            'CLASSIFICATION_IS_NOT_DELETION_AUTHORITY',
            'ABSENCE_FROM_ACTIVE_WORKSPACE_DOES_NOT_IMPLY_ABSENCE_FROM_SYSTEM_STATE'
        ],
        'functional_roles': {
            'MATERIAL_ACTIVE': 'Core component in primary calculation chain',
            'MATERIAL_DELAYED': 'Initially dormant component required at a later consequence step (requires C3-R restore)',
            'MATERIAL_REACTIVATED': 'Early sub-result that leaves active workspace and must be restored in Phase 3 (requires C3-R restore)',
            'DECOY_DISPENSABLE': 'Plausible contextual distractor that remains 100% dispensable (restoring is False Positive)',
            'RESOLVED_TERMINAL': 'Fully absorbed sub-calculation that must never be reopened (restoring is False Positive)'
        },
        'task_pairs': {}
    }

    for fam in families:
        fid = fam['id']
        dep_map['task_pairs'][fid] = {
            'pair_id': fid,
            'tier': fam['tier'],
            'name': fam['name'],
            'required_intermediate_values': fam['required_intermediates'],
            'material_edges': fam['edges'],
            'components': fam['components'],
            'consequence_step': fam['consequence_step'],
            'restore_targets': fam['restore_targets'],
            'decoy_components': fam['decoy_components'],
            'terminal_components': fam['terminal_components']
        }

        task_a = {
            'task_id': f'{fid}-A',
            'pair_id': fid,
            'form': 'A',
            'prompt': fam['prompt_core']
        }
        task_b = {
            'task_id': f'{fid}-B',
            'pair_id': fid,
            'form': 'B',
            'prompt': f'Solve the same quantity problem, writing intermediate values before the final result: {fam["prompt_core"]}'
        }

        task_set.extend([task_a, task_b])
        answer_key.append({'task_id': f'{fid}-A', 'pair_id': fid, 'answer': fam['answer']})
        answer_key.append({'task_id': f'{fid}-B', 'pair_id': fid, 'answer': fam['answer']})

    assert len(task_set) == 72
    assert len(answer_key) == 72

    seed_str = 'NJAL-R01-2026-09-12-FROZEN-SEED'
    cond_cycle = ['C2', 'C3-I', 'C3-R']
    assignments = []

    for tier_name in ['local_short_horizon', 'delayed_dependency', 'reactivation']:
        tier_pairs = [f for f in families if f['tier'] == tier_name]
        for p_idx, fam in enumerate(tier_pairs):
            fid = fam['id']
            c_a = cond_cycle[(p_idx * 2) % 3]
            order_a = int(hashlib.sha256(f'{seed_str}:{fid}-A'.encode()).hexdigest()[:8], 16)
            assignments.append({
                'task_id': f'{fid}-A',
                'pair_id': fid,
                'form': 'A',
                'condition': c_a,
                'order': order_a
            })
            c_b = cond_cycle[(p_idx * 2 + 1) % 3]
            order_b = int(hashlib.sha256(f'{seed_str}:{fid}-B'.encode()).hexdigest()[:8], 16)
            assignments.append({
                'task_id': f'{fid}-B',
                'pair_id': fid,
                'form': 'B',
                'condition': c_b,
                'order': order_b
            })

    # Validate assignment counts
    cond_counts = {}
    tier_cond_counts = {}
    form_cond_counts = {}
    for a in assignments:
        c = a['condition']
        cond_counts[c] = cond_counts.get(c, 0) + 1
        form = a['form']
        form_cond_counts[(form, c)] = form_cond_counts.get((form, c), 0) + 1
        pair_tier = next(f['tier'] for f in families if f['id'] == a['pair_id'])
        tier_cond_counts[(pair_tier, c)] = tier_cond_counts.get((pair_tier, c), 0) + 1

    assert cond_counts == {'C2': 24, 'C3-I': 24, 'C3-R': 24}, f'Imbalance: {cond_counts}'
    for form in ['A', 'B']:
        for c in ['C2', 'C3-I', 'C3-R']:
            assert form_cond_counts[(form, c)] == 12, f'Form imbalance: {form_cond_counts}'
    for tier in ['local_short_horizon', 'delayed_dependency', 'reactivation']:
        for c in ['C2', 'C3-I', 'C3-R']:
            assert tier_cond_counts[(tier, c)] == 8, f'Tier imbalance: {tier_cond_counts}'

    manifest = {
        'protocol': 'NJAL-R01',
        'version': '0.1',
        'frozen_at': '2026-09-12',
        'seed': seed_str,
        'task_count': 72,
        'task_families': 36,
        'condition_counts': {
            'C2': 24,
            'C3-I': 24,
            'C3-R': 24
        },
        'tier_condition_counts': {
            'local_short_horizon': {'C2': 8, 'C3-I': 8, 'C3-R': 8},
            'delayed_dependency': {'C2': 8, 'C3-I': 8, 'C3-R': 8},
            'reactivation': {'C2': 8, 'C3-I': 8, 'C3-R': 8}
        },
        'form_condition_counts': {
            'A': {'C2': 12, 'C3-I': 12, 'C3-R': 12},
            'B': {'C2': 12, 'C3-I': 12, 'C3-R': 12}
        },
        'scorer_blinding': 'condition, executor identity, prompts, and structural condition scaffolding hidden',
        'assignment_rule': 'balanced cyclic condition assignment with deterministic sha256 order key; do not reshuffle after execution',
        'files': [
            'task-set-v0.1.jsonl',
            'answer-key-v0.1.jsonl',
            'dependency-map-v0.1.json',
            'assignment-manifest-v0.1.json',
            'audit-log-template.jsonl'
        ],
        'assignments': assignments
    }

    audit_template = [
        {'event_type': 'PROTOCOL_SEALED', 'protocol': 'NJAL-R01', 'version': '0.1', 'seed': seed_str},
        {'event_type': 'NEED_DECLARED', 'task_id': 'EXAMPLE', 'component_id': 'C1', 'reason': 'required_for_step'},
        {'event_type': 'COMPONENT_ACTIVATED', 'task_id': 'EXAMPLE', 'component_id': 'C1'},
        {'event_type': 'COMPONENT_MARKED_CANDIDATE_REMOVE', 'task_id': 'EXAMPLE', 'component_id': 'C3'},
        {'event_type': 'COMPONENT_MOVED_LATENT', 'task_id': 'EXAMPLE', 'component_id': 'C3'},
        {'event_type': 'COMPONENT_REMOVED_IRREVERSIBLE', 'task_id': 'EXAMPLE', 'component_id': 'C3'},
        {'event_type': 'DEPENDENCY_MISSING', 'task_id': 'EXAMPLE', 'component_id': 'C1'},
        {'event_type': 'RESTORE_REQUESTED', 'task_id': 'EXAMPLE', 'component_id': 'C1', 'downstream_step': 3},
        {'event_type': 'COMPONENT_RESTORED', 'task_id': 'EXAMPLE', 'component_id': 'C1'},
        {'event_type': 'CONSEQUENCE_STEP', 'task_id': 'EXAMPLE', 'step_index': 3},
        {'event_type': 'FINAL_ANSWER', 'task_id': 'EXAMPLE', 'submitted_answer': 42}
    ]

    tasks_path = runs_dir / 'task-set-v0.1.jsonl'
    with open(tasks_path, 'w', encoding='utf-8') as f:
        for t in task_set:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    ans_path = runs_dir / 'answer-key-v0.1.jsonl'
    with open(ans_path, 'w', encoding='utf-8') as f:
        for a in answer_key:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")

    dep_path = runs_dir / 'dependency-map-v0.1.json'
    with open(dep_path, 'w', encoding='utf-8') as f:
        json.dump(dep_map, f, indent=2, ensure_ascii=False)
        f.write("\n")

    manifest_path = runs_dir / 'assignment-manifest-v0.1.json'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    audit_path = runs_dir / 'audit-log-template.jsonl'
    with open(audit_path, 'w', encoding='utf-8') as f:
        for item in audit_template:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    hashes = {}
    for p in [tasks_path, ans_path, dep_path, manifest_path, audit_path]:
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        hashes[p.name] = h

    print('NJAL-R01 artifacts generated and sealed successfully:')
    for fname, h in hashes.items():
        print(f'  {fname}: {h}')

    preflight_path = runs_dir / 'preflight-v0.1.json'
    if preflight_path.exists():
        with open(preflight_path, 'r', encoding='utf-8') as f:
            preflight = json.load(f)
        
        preflight['execution_gate']['task_set_frozen'] = True
        preflight['execution_gate']['dependency_map_frozen'] = True
        preflight['execution_gate']['randomization_seed_frozen'] = True
        preflight['execution_gate']['assignment_manifest_frozen'] = True
        preflight['execution_gate']['artifact_sha256'] = hashes
        preflight['next_gate'] = 'verify condition-neutral scorer handoff, executor isolation, and model configuration'
        
        with open(preflight_path, 'w', encoding='utf-8') as f:
            json.dump(preflight, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print('Updated preflight-v0.1.json execution gates.')

if __name__ == '__main__':
    generate_all()

from copy import deepcopy

from cobra.io.sbml import create_cobra_model_from_sbml_file
from cobra.core import Reaction, Metabolite, Formula


def init_wt_model(model_name, carbon_sources, BM_lower_bound=0.1):
    if model_name == 'ecoli_core':
        model = create_cobra_model_from_sbml_file('data/ecoli_core.xml', old_sbml=True)

        # the core model has these annoying '_b' metabolites that are used as
        # 'ghost' metabolites that balance the exchange reactions. they should
        # be ignored in the mass-balance equation and therefore the best way to
        # deal with them is to remove them from all the reactions
        for m in model.metabolites:
            if m.endswith('_b'):
                for r in m.get_reaction():
                    coeff = r.get_coefficient(m)
                    r.add_metabolites({m : -coeff})

        rxns = dict([(r.id, r) for r in model.reactions])
        rxns['ATPM'].lower_bound = 0 # remove the ATP maintenance requirement
        rxns['EX_glc_e'].lower_bound = 0 # remove the default carbon source
    elif model_name == 'iJO1366':
        model = create_cobra_model_from_sbml_file('data/iJO1366.xml', old_sbml=True)
        rxns = dict([(r.id, r) for r in model.reactions])
        rxns['ATPM'].lower_bound = 0 # remove the ATP maintenance requirement
        rxns['EX_glc_e'].lower_bound = 0 # remove the default carbon source
    else:
        model = create_cobra_model_from_sbml_file('data/%s.xml' % model_name)
        
    for key, val in carbon_sources.iteritems():
        set_exchange_bounds(model, key, val, upper_bound=0)
        
    # set BM lower bound
    for r in model.reactions:
        if r.objective_coefficient != 0:
            r.lower_bound = BM_lower_bound
    
    return model


def clone_model(model):
    return deepcopy(model)


def add_metabolite(model, id, formula, name, compartment='C'):
    try:
        model.metabolites.index(id)
    except Exception, e:
        # CobraPy versions differ in what error they raise,
        # hence catching base Exception.
        met = Metabolite(id=id, formula=Formula(formula),
                            name=name, compartment=compartment)
        model.add_metabolites([met])


def knockout_reactions(model, ko_reactions):
    for r in ko_reactions.split(','):
        model.remove_reactions(r)


def add_reaction(model, id, name, sparse,
                 lower_bound=0, upper_bound=1000):
    """
        Adds a reaction to the model
    """
    # convert the sparse representation using the metabolites in the model
    for key in sparse.keys():
        if key not in model.metabolites:
            raise Exception("cannot find the cytoplasmic metabolite %s in the model" % key)

    r = dict([(model.metabolites[model.metabolites.index(key)], val)
              for key, val in sparse.iteritems()])
    reaction = Reaction(name)
    reaction.id = id
    reaction.add_metabolites(r)
    reaction.lower_bound = lower_bound
    reaction.upper_bound = upper_bound
    model.add_reactions([reaction])
    return reaction


def knockin_reactions(model, ki_reactions, lower_bound=None, upper_bound=1000):
    for rid in ki_reactions.split(','):
        if rid.startswith('EX_'):
            rid = rid[3:]
            if lower_bound is None:
                add_metabolite_exchange(model, rid, 0, upper_bound)
            else:
                add_metabolite_exchange(model, rid, lower_bound, upper_bound)
            continue
        
        reversible = False
        
        if rid == 'PRK':
            add_metabolite(model, 'rubp_D_c', 'C5H12O11P2', 'D-ribulose 1,5-bisphosphate')
            sprs = {'ru5p_D_c': -1, 'atp_c': -1,
                    'rubp_D_c': 1, 'adp_c': 1}
            name = 'phosphoribulokinase'
        elif rid == 'RBC':
            add_metabolite(model, 'rubp_D_c', 'C5H12O11P2', 'D-ribulose 1,5-bisphosphate')
            sprs = {'rubp_D_c': -1, 'h2o_c': -1,
                    'co2_c': -1, '3pg_c': 2, 'h_c' : 3}
            name = 'RuBisCO'
        elif rid == 'EDD':
            add_metabolite(model, '2ddg6p_c', 'C6H8O9P', '2-dehydro-3-deoxy-D-gluconate 6-phosphate')
            sprs = {'6pgc_c' : -1, 'h2o_c' : 1, '2ddg6p_c' : 1}
            name = '6-phosphogluconate dehydratase'
        elif rid == 'EDA':
            add_metabolite(model, '2ddg6p_c', 'C6H8O9P', '2-dehydro-3-deoxy-D-gluconate 6-phosphate')
            sprs = {'2ddg6p_c' : -1, 'g3p_c' : 1, 'pyr_c' : 1}
            name = '2-dehydro-3-deoxy-phosphogluconate aldolase'
        elif rid == 'PKT':
            sprs = {'f6p_c' : -1, 'pi_c' : -1, 'e4p_c' : 1, 'actp_c' : 1, 'h2o_c' : 1}
            name = 'phosphoketolase'
        elif rid == 'RED':
            sprs = {'nad_c' : -1, 'nadh_c' : 1}
            name = 'free_e'
        elif rid == 'MCS':
            add_metabolite(model, 'malcoa_c', 'C25H40N7O20P3S', 'Malyl-CoA')
            sprs = {'mal_L_c':-1, 'atp_c':-1, 'coa_c':-1, 'malcoa_c':1, 'adp_c':1, 'pi_c':1}
            name = 'malyl-CoA synthase'
            reversible = True
        elif rid == 'MCL':
            add_metabolite(model, 'malcoa_c', 'C25H40N7O20P3S', 'Malyl-CoA')
            sprs = {'malcoa_c':-1, 'accoa_c':1, 'glx_c':1}
            name = 'malyl-CoA lyase'
        elif rid == 'SBP':
            add_metabolite(model, 'sbp_c', 'C7H16O13P2', 'D-sedoheptulose 1,7-bisphosphate')
            sprs = {'sbp_c':-1, 'h2o_c':-1, 's7p_c':1, 'pi_c':1}
            name = 'sedoheptulose bisphosphate phosphatase'
        elif rid == 'SBA':
            add_metabolite(model, 'sbp_c', 'C7H16O13P2', 'D-sedoheptulose 1,7-bisphosphate')
            sprs = {'sbp_c':-1, 'g3p_c':1, 'e4p_c':1}
            name = 'sedoheptulose bisphosphate aldolase'
            reversible = True
        else:
            raise Exception('unknown knockin reaction: ' + rid)

        if lower_bound is None:
            if reversible:
                add_reaction(model, rid, name, sprs, -1000, upper_bound)
            else:
                add_reaction(model, rid, name, sprs, 0, upper_bound)
        else:
            add_reaction(model, rid, name, sprs, lower_bound, upper_bound)
            
def add_metabolite_exchange(model, metabolite, lower_bound, upper_bound=0):
    try:
        met = model.metabolites[model.metabolites.index(metabolite + '_c')]
    except AttributeError:
        raise KeyError('Model does not have a metabolite with ID: ' + metabolite)
    
    add_metabolite(model, metabolite + '_e', str(met.formula), met.name, 'E')
    add_reaction(model, metabolite + '_transport', met.name + ' permease',
                 {metabolite + '_c' : -1, metabolite + '_e' : 1}, -1000, 1000)
                 
    add_reaction(model, 'EX_' + metabolite + '_e', met.name + ' exchange',
                 {metabolite + '_e' : -1}, lower_bound, upper_bound)

def set_exchange_bounds(model, metabolite, lower_bound, upper_bound=0):
    rxns = dict([(r.id, r) for r in model.reactions])
    try:
        rxns['EX_' + metabolite + '_e'].lower_bound = lower_bound
        rxns['EX_' + metabolite + '_e'].upper_bound = upper_bound
    except KeyError:
        add_metabolite_exchange(model, metabolite, lower_bound, upper_bound)
        
    

import os
from string import ascii_letters
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
from utils.utils import load_data
from constants import *
from policy.policy import GreedyPolicy, StochasticPolicy

def physician_action_consistency_in_two_datasets(df_train, df_val, img_path, plot_suffix, FONT_SIZE):
    train_action_dist = df_train.groupby(['state'])['action'].apply(lambda x : x.value_counts().index[0])
    df_all = pd.concat([df_train[['state', 'action']], df_val[['state', 'action']]])
    all_action_dist = df_all.groupby(['state'])['action'].apply(lambda x : x.value_counts().index[0])
    
    same_mode = sum(train_action_dist.values == all_action_dist.values)
    diff_mode = sum(train_action_dist.values != all_action_dist.values)

    fig, ax = plt.subplots(figsize=(10, 10))
    objects = ('Consistent', 'Inconsistent')
    y_pos = np.arange(len(objects))
    performance = [same_mode, diff_mode]

    plt.bar(y_pos, performance, align='center')
    plt.xticks(y_pos, objects, fontsize = FONT_SIZE)
    plt.ylabel('Number of states', fontsize = FONT_SIZE)
    plt.title('Physician mode action in \n train vs train+val', fontsize = FONT_SIZE)
 
    fig.savefig('{}{}'.format(img_path, plot_suffix), ppi=300)

def controversial_states(df, img_path, plot_suffix, FONT_SIZE):
	df_mod = df[['state','action']]
	df_mod['iv_action'] = df_mod['action'] % 5
	df_mod['vaso_action'] = df_mod['action'] // 5
	
	# Number of unique actions across states
	df_unique = df_mod.groupby(['state']).nunique()

	fig = plt.figure(figsize = (25, 10))
	ax1 = fig.add_subplot(121)
	ax1.hist(df_unique['iv_action'].astype(int))
	ax1.set_title("Unique IV actions across states", fontsize = FONT_SIZE)
	ax1.set_xlabel("Number of unique IV actions", fontsize = FONT_SIZE)
	ax1.set_ylabel("Number of States", fontsize = FONT_SIZE)
	# plt.show()

	ax2 = fig.add_subplot(122)
	ax2.hist(df_unique['vaso_action'].astype(int))
	ax2.set_title("Unique vaso actions across states", fontsize = FONT_SIZE)
	ax2.set_xlabel("Number of unique vaso actions", fontsize = FONT_SIZE)
	ax2.set_ylabel("Number of States", fontsize = FONT_SIZE)
	# plt.show()
	
	fig.savefig('{}{}'.format(img_path, plot_suffix), ppi=300)

def action_variance(df, img_path, plot_suffix, FONT_SIZE):
	df_mod = df[['state','action']]
	df_mod['iv_action'] = df_mod['action'] % 5
	df_mod['vaso_action'] = df_mod['action'] // 5
	# action variance across states
	df_var = df_mod.groupby(['state']).std()
	df_count = df_mod.groupby(['state']).count()
	all_action_stderr = np.array(df_var['action']/np.sqrt(df_count['action']))
	iv_stderr = np.array(df_var['iv_action']/np.sqrt(df_count['iv_action']))
	vaso_stderr = np.array(df_var['vaso_action']/np.sqrt(df_count['vaso_action']))

	fig = plt.figure(figsize = (40, 10))
	ax1 = fig.add_subplot(131)

	ax1.hist(all_action_stderr, bins = 20)
	ax1.set_title("Standard error of \n 25 actions", fontsize = FONT_SIZE)
	ax1.set_xlabel("Standard error of action", fontsize = FONT_SIZE)
	ax1.set_ylabel("Number of States", fontsize = FONT_SIZE)

	ax2 = fig.add_subplot(132)
	ax2.hist(vaso_stderr, bins = 20)
	ax2.set_title("Standard error of \n 5 vaso actions", fontsize = FONT_SIZE)
	ax2.set_xlabel("Standard error of vaso action", fontsize = FONT_SIZE)
	ax2.set_ylabel("Number of States", fontsize = FONT_SIZE)

	ax3 = fig.add_subplot(133)
	ax3.hist(iv_stderr, bins = 20)
	ax3.set_title("Standard error of \n 5 IV actions", fontsize = FONT_SIZE)
	ax3.set_xlabel("Standard error of IV action", fontsize = FONT_SIZE)
	ax3.set_ylabel("Number of States", fontsize = FONT_SIZE)
	
	fig.savefig('{}{}'.format(img_path, plot_suffix), ppi=300)
	return all_action_stderr, iv_stderr, vaso_stderr

def policy_matrix(expert_filepath, irl_expert_filepath,
                        plot_suffix, trial_num, iter_num, verbose=False):
	q_star_path = '{}_t{}xi{}.npy'.format(expert_filepath, trial_num, iter_num)
	irl_path = '{}_t{}xi{}.npy'.format(irl_expert_filepath, trial_num, iter_num)
	Q_star = np.load(q_star_path)[:NUM_PURE_STATES+1, :]
	Q_irl = np.load(irl_path)[:NUM_PURE_STATES+1, :]

	pi_physician_greedy = GreedyPolicy(NUM_PURE_STATES, NUM_ACTIONS, Q_star).get_opt_actions()
	pi_physician_stochastic = StochasticPolicy(NUM_PURE_STATES, NUM_ACTIONS, Q_star).query_Q_probs()
	opt_policy_learned = StochasticPolicy(NUM_PURE_STATES, NUM_ACTIONS, Q_irl).query_Q_probs()
	return pi_physician_greedy, pi_physician_stochastic, opt_policy_learned

def find_consensus_low_var_low_KL_states(all_action_stderr, iv_stderr, vaso_stderr, plot_suffix, DATA_PATH, img_path, date, trial_num, iter_num, verbose=False):
	KL_path = '{}_t{}xi{}_KL.npy'.format(DATA_PATH + date + plot_suffix, trial_num, iter_num)

	KL = np.load(KL_path)

	KL_IRL = []
	# KL_random = []
	# KL_vaso_random = []
	# KL_iv_random = []
	# KL_no_int = []

	keys = list(KL.item().keys())

	for state in keys:
		KL_IRL.append(KL.item()[state]["IRL"])
		# KL_random.append(KL[state]["random"])
		# KL_no_int.append(KL[state]["no_int_policy"])
		# KL_vaso_random.append(KL[state]["vaso_only_random"])
		# KL_iv_random.append(KL[state]["iv_only_random"])

	KL_IRL = np.array(KL_IRL)
	# OVERLAP: TOP 20% least KL-diverged states AND Top 20% low stderr states
	percent = 0.2
	number_states_to_compare = int(percent*750)
	inds_KL = KL_IRL.argsort()[:number_states_to_compare]
	inds_all_action = all_action_stderr.argsort()[:number_states_to_compare]
	low_kl_low_stderr_states = np.intersect1d(inds_KL, inds_all_action)
	# OVERLAP: TOP 20% least KL-diverged states AND Top 20%  low iv stderr states
	percent = 0.2
	number_states_to_compare = int(percent*750)
	inds_KLfor_iv = KL_IRL.argsort()[:number_states_to_compare]
	inds_iv = iv_stderr.argsort()[:number_states_to_compare]
	low_kl_low_iv_stderr_states = np.intersect1d(inds_KLfor_iv, inds_iv)
	# OVERLAP: TOP 20% least KL-diverged states AND Top 20% low vaso stderr states
	percent = 0.2
	number_states_to_compare = int(percent*750)
	inds_KLfor_vaso = KL_IRL.argsort()[:number_states_to_compare]
	inds_vaso = vaso_stderr.argsort()[:number_states_to_compare]
	low_kl_low_vaso_stderr_states = np.intersect1d(inds_KLfor_vaso, inds_vaso)
	print (low_kl_low_stderr_states.shape, low_kl_low_iv_stderr_states.shape, low_kl_low_vaso_stderr_states.shape)
	return low_kl_low_stderr_states, low_kl_low_iv_stderr_states, low_kl_low_vaso_stderr_states


def find_consensus_high_var_high_KL_states(all_action_stderr, iv_stderr, vaso_stderr, plot_suffix, DATA_PATH, img_path, date, trial_num, iter_num, verbose=False):
	KL_path = '{}_t{}xi{}_KL.npy'.format(DATA_PATH + date + plot_suffix, trial_num, iter_num)

	KL = np.load(KL_path)

	KL_IRL = []
	# KL_random = []
	# KL_vaso_random = []
	# KL_iv_random = []
	# KL_no_int = []

	keys = list(KL.item().keys())

	for state in keys:
		KL_IRL.append(KL.item()[state]["IRL"])
		# KL_random.append(KL[state]["random"])
		# KL_no_int.append(KL[state]["no_int_policy"])
		# KL_vaso_random.append(KL[state]["vaso_only_random"])
		# KL_iv_random.append(KL[state]["iv_only_random"])

	KL_IRL = np.array(KL_IRL)
	# OVERLAP: TOP 20% most KL-diverged states AND Top 20% high stderr states
	percent = 0.2
	number_states_to_compare = int(percent*750)
	inds_KL = KL_IRL.argsort()[-number_states_to_compare:][::-1]
	inds_all_action = all_action_stderr.argsort()[-number_states_to_compare:][::-1]
	high_kl_high_stderr_states = np.intersect1d(inds_KL, inds_all_action)
	# OVERLAP: TOP 20% most KL-diverged states AND Top 20% high iv stderr states
	percent = 0.2
	number_states_to_compare = int(percent*750)
	inds_KLfor_iv = KL_IRL.argsort()[-number_states_to_compare:][::-1]
	inds_iv = iv_stderr.argsort()[-number_states_to_compare:][::-1]
	high_kl_high_iv_stderr_states = np.intersect1d(inds_KLfor_iv, inds_iv)
	# OVERLAP: TOP 20% most KL-diverged states AND Top 20% high vaso stderr states
	percent = 0.2
	number_states_to_compare = int(percent*750)
	inds_KLfor_vaso = KL_IRL.argsort()[-number_states_to_compare:][::-1]
	inds_vaso = vaso_stderr.argsort()[-number_states_to_compare:][::-1]
	high_kl_high_vaso_stderr_states = np.intersect1d(inds_KLfor_vaso, inds_vaso)

	print (high_kl_high_stderr_states.shape, high_kl_high_iv_stderr_states.shape, high_kl_high_vaso_stderr_states.shape)
	return high_kl_high_stderr_states, high_kl_high_iv_stderr_states, high_kl_high_vaso_stderr_states

def plot_expert_irl_action_distribution(concensus_states, expert_policy_matrix, agent_policy_matrix, img_path, plot_suffix, num_states_to_plot=20):
	assert (expert_policy_matrix.shape == agent_policy_matrix.shape), "The sa_matrices have different dimensions."

        # plot maximum 20 states
	fig, ((ax1, ax2, ax3, ax4, ax5), (ax6, ax7, ax8, ax9, ax10), 
	        (ax11, ax12, ax13, ax14, ax15), (ax16, ax17, ax18, ax19, ax20)) = plt.subplots(4, 5, figsize=(20, 10))
	graph = ((ax1, ax2, ax3, ax4, ax5), (ax6, ax7, ax8, ax9, ax10), 
	        (ax11, ax12, ax13, ax14, ax15), (ax16, ax17, ax18, ax19, ax20))
	width = 0.5

	indices = np.arange(expert_policy_matrix.shape[1])
	
	for i in range(min(len(concensus_states), 20)):
	    expert_dist = expert_policy_matrix[concensus_states[i],:]
	    agent_dist = agent_policy_matrix[concensus_states[i],:]	
	    
	    row_ind = int(i//5)
	    column_ind = int(i-row_ind*5)
	    
	    graph[row_ind][column_ind].bar(indices, expert_dist, width=width, 
	            color='b', alpha = 0.8, label='Expert action')
	    graph[row_ind][column_ind].bar(indices, agent_dist, 
	            width=0.5*width, color='r', alpha=0.8, label='Agent action')
	    graph[row_ind][column_ind].set_ylim([0,1])
	    graph[row_ind][column_ind].set_xticks(indices, 
	               ['T{}'.format(i) for i in range(len(concensus_states))] )
	plt.legend(loc='center left', bbox_to_anchor=(1, 1))

	fig.savefig('{}{}'.format(img_path, plot_suffix), ppi=300)


def plot_feature_corr(df_train, img_path):

	# Compute the correlation matrix
	corr = df_train.iloc[:, :-8].corr()

	# Generate a mask for the upper triangle
	mask = np.zeros_like(corr, dtype=np.bool)
	mask[np.triu_indices_from(mask)] = True

	# Set up the matplotlib figure
	fig, ax = plt.subplots(figsize=(20, 15))

	# Generate a custom diverging colormap
	cmap = sns.diverging_palette(220, 10, as_cmap=True)

	# Draw the heatmap with the mask and correct aspect ratio
	sns.heatmap(corr, mask=mask, cmap=cmap, vmax=.6, center=0,
				square=True, linewidths=.5, cbar_kws={"orientation": "horizontal", "shrink": .5})
	# plt.show()
	print ("saving corr plot to ", img_path)
	fig.savefig('{}feature_corr_plot'.format(img_path), ppi=300, bbox_inches='tight')



# Need controversial states, high KL_states
if __name__ == '__main__':
	FONT_SIZE = 35
	# font = {'weight' : 'bold',
	#         'size'   : FONT_SIZE}
	# plt.rc('font', **font)

	df_train, df_val, df_centroids, df_full = load_data()
	df = df_train[df_centroids.columns]
	date = '2017_12_09/'

	# pick which models you want manually for now...
	trial_num = 5
	iter_num = 15
	if not os.path.exists(DATA_PATH + date):
		raise Exception('desired date should be specified for loading saved data.')
	else:
		img_path = DATA_PATH + date + IMG_PATH

	phy_q_filepath = DATA_PATH + date + PHYSICIAN_Q
	# irl_phy_q_greedy_filepath = DATA_PATH + date + IRL_PHYSICIAN_Q_GREEDY
	irl_phy_q_stochastic_filepath = DATA_PATH + date + IRL_PHYSICIAN_Q_STOCHASTIC

	# # unique actions per state
	# plot_unique_action = 'unique_actions_per_state'
	# controversial_states(df_train, img_path, plot_unique_action, FONT_SIZE)
	# # action variance
	# plot_action_variance = 'action_variance'
	# action_variance(df_train, img_path, plot_action_variance, FONT_SIZE)


	# # Stochasticity analysis
	# plot_mode_consistency = 'mode_consistency'
	# physician_action_consistency_in_two_datasets(df_train, df_val, img_path, plot_mode_consistency, FONT_SIZE)

	plot_feature_corr(df_train, img_path)


	plot_phy_greedy_id = 'greedy_physician'
	plot_phy_stochastic_id = 'stochastic_physician'

	all_action_stderr, iv_stderr, vaso_stderr = controversial_states(df_train, img_path)
	high_kl_high_stderr_states, high_kl_high_iv_stderr_states, high_kl_high_vaso_stderr_states = \
	find_consensus_high_var_high_KL_states(all_action_stderr, iv_stderr, vaso_stderr, plot_phy_stochastic_id, DATA_PATH, img_path, 
		date, trial_num, iter_num, verbose=False)
	low_kl_low_stderr_states, low_kl_low_iv_stderr_states, low_kl_low_vaso_stderr_states = \
	find_consensus_low_var_low_KL_states(all_action_stderr, iv_stderr, vaso_stderr, plot_phy_stochastic_id, DATA_PATH, img_path, 
		date, trial_num, iter_num, verbose=False)
	pi_physician_greedy, pi_physician_stochastic, opt_policy_learned = policy_matrix(phy_q_filepath, irl_phy_q_stochastic_filepath,
		plot_phy_stochastic_id, trial_num, iter_num, verbose=False)
	success_states = 'success_states'
	success_iv_states = 'success_iv_states'
	success_vaso_states = 'success_vaso_states'
	failure_states = 'failure_states'
	failure_iv_states = 'failure_iv_states'
	failure_vaso_states = 'failure_vaso_states'
	plot_expert_irl_action_distribution(low_kl_low_stderr_states, pi_physician_stochastic, opt_policy_learned, img_path, success_states, num_states_to_plot=20)
	plot_expert_irl_action_distribution(low_kl_low_iv_stderr_states, pi_physician_stochastic, opt_policy_learned, img_path, success_iv_states, num_states_to_plot=20)
	plot_expert_irl_action_distribution(low_kl_low_vaso_stderr_states, pi_physician_stochastic, opt_policy_learned, img_path, success_vaso_states, num_states_to_plot=20)
	plot_expert_irl_action_distribution(high_kl_high_stderr_states, pi_physician_stochastic, opt_policy_learned, img_path, failure_states, num_states_to_plot=20)
	plot_expert_irl_action_distribution(high_kl_high_iv_stderr_states, pi_physician_stochastic, opt_policy_learned, img_path, failure_iv_states, num_states_to_plot=20)
	plot_expert_irl_action_distribution(high_kl_high_vaso_stderr_states, pi_physician_stochastic, opt_policy_learned, img_path, failure_vaso_states, num_states_to_plot=20)


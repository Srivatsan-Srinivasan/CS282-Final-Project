import os, errno
import datetime
import numpy as np
import numba as nb
import pandas as pd

from scipy import stats
from sklearn.decomposition import PCA
from sklearn.cluster import MiniBatchKMeans
from sklearn import preprocessing
from constants import *
import pickle
from kmodes.kprototypes import KPrototypes

def check_numerical_categorical(all_cols, categorical_cols, numerical_cols):
    check1 = (set(numerical_cols) - set(all_cols))
    #print(check1)
    check2 = (set(categorical_cols) - set(all_cols))
    #print(check2)
    check3 = (set(all_cols) - set(categorical_cols) - set(numerical_cols))
    #print(check3)
    return (check1 | check2 | check3) == set(ETC)

def save_data(obj, path):
    with open(path, 'wb') as f:
        pickle.dump(obj, f)


def save_Q(Q, save_path, num_trials, num_iterations, data_name):
    # TODO: check for instance of class and make sure to save Q instead of an instance
    np.save('{}{}_t{}xi{}'.format(save_path, data_name, num_trials, num_iterations), Q)


def detect_binary_value_columns(df):
    '''
    return:
        a list of columns names with binary values
    '''
    return [col for col in df if df[col].dropna().value_counts().index.isin([0,1]).all()]


def load_data(generate_new_data=False,
              num_states=(NUM_STATES-NUM_TERMINAL_STATES)):
    # @todo append num_states to filename
    if not generate_new_data and os.path.isfile(TRAIN_CLEANSED_DATA_FILEPATH) and os.path.isfile(VALIDATE_CLEANSED_DATA_FILEPATH):
        print('loading preprocessed data as they already exist')
        df_cleansed_train = _load_data(TRAIN_CLEANSED_DATA_FILEPATH)
        df_cleansed_val = _load_data(VALIDATE_CLEANSED_DATA_FILEPATH)
        df_centroids_train = _load_data(TRAIN_CENTROIDS_DATA_FILEPATH)

        #df_cleansed_train_kp = _load_data(TRAIN_CLEANSED_KP_DATA_FILEPATH)
        #df_cleansed_val_kp = _load_data(VALIDATE_CLEANSED_KP_DATA_FILEPATH)
        #df_centroids_train_kp = _load_data(TRAIN_CENTROIDS_KP_DATA_FILEPATH)

        df_cleansed_pca_train = _load_data(TRAIN_CLEANSED_PCA_DATA_FILEPATH)
        df_cleansed_pca_val = _load_data(VALIDATE_CLEANSED_PCA_DATA_FILEPATH)
        df_centroids_pca_train = _load_data(TRAIN_CENTROIDS_PCA_DATA_FILEPATH)
    else:
        print('processing data from scratch')
        df_train = _load_data(TRAIN_FILEPATH)
        df_val = _load_data(VALIDATE_FILEPATH)
        assert not df_train.isnull().values.any(), "there's null values in df_train"
        assert not df_val.isnull().values.any(), "there's null values in df_val"
        print('correcting obvious errors')
        df_corrected_train, df_corrected_val = correct_data(df_train, df_val)
        assert not df_corrected_train.isnull().values.any(), "there's null values in df_corrected_train"
        assert not df_corrected_val.isnull().values.any(), "there's null values in df_corrected_val"
        print('standardizing data')
        df_norm_train, df_norm_val = normalize_data(df_corrected_train,
                                                    df_corrected_val)
        assert not df_norm_train.isnull().values.any(), "there's null values in df_norm_train"
        assert not df_norm_val.isnull().values.any(), "there's null values in df_norm_val"
        # separate x mu y from df
        X_train, mu_train, y_train, X_val, mu_val, y_val = \
                separate_X_mu_y(df_norm_train, df_norm_val, ALL_VALUES)

        # save for for pca before clustering
        X_pca_train = X_train.copy()
        X_pca_val = X_val.copy()

        # k-means clustering to consturct discrete states
        print('clustering for states')
        X_to_cluster_train = X_train.drop(COLS_NOT_FOR_CLUSTERING, axis=1)
        X_to_cluster_val = X_val.drop(COLS_NOT_FOR_CLUSTERING, axis=1)
        df_centroids_train, X_clustered_train, X_clustered_val = \
            clustering(X_to_cluster_train, X_to_cluster_val, k=num_states, batch_size=300)

        # k-means stitching up
        print('saving processed data')
        to_concat_train = [X_clustered_train, X_train, mu_train, y_train]
        to_concat_val = [X_clustered_val, X_val, mu_val, y_val]

        df_cleansed_train = pd.concat(to_concat_train, axis=1)
        df_cleansed_val = pd.concat(to_concat_val, axis=1)
        df_centroids_train.to_csv(TRAIN_CENTROIDS_DATA_FILEPATH, index=False)
        df_cleansed_train.to_csv(TRAIN_CLEANSED_DATA_FILEPATH, index=False)
        df_cleansed_val.to_csv(VALIDATE_CLEANSED_DATA_FILEPATH, index=False)

        # k-prototyp separate x mu y from df
        #df_norm_train_kp, df_norm_val_kp = normalize_data(df_corrected_train,
        #                                                  df_corrected_val,
        #                                                  normalize_categorical=False)
        #assert not df_norm_train_kp.isnull().values.any(), "there's null values in df_norm_train"
        #assert not df_norm_val_kp.isnull().values.any(), "there's null values in df_norm_val"


        #X_train_kp, mu_train_kp, y_train_kp, X_val_kp, mu_val_kp, y_val_kp = \
        #        separate_X_mu_y(df_norm_train_kp, df_norm_val_kp, ALL_VALUES)

        ## k-prototype clustering (Cao) to construct discrete states
        #print('k prototype clustering')
        #X_to_cluster_train_kp = X_train_kp.drop(COLS_NOT_FOR_CLUSTERING, axis=1)
        #X_to_cluster_val_kp = X_val_kp.drop(COLS_NOT_FOR_CLUSTERING, axis=1)
        ## k-prototyp separate x mu y from df
        #df_centroids_train_kp, X_clustered_train_kp, X_clustered_val_kp = \
        #    clustering_kp(X_to_cluster_train_kp, X_to_cluster_val_kp, num_states=num_states)

        ## k-prototype stitching up
        #print('k prototype stitching up')
        #to_concat_train_kp = [X_clustered_train_kp, X_train_kp, mu_train_kp, y_train_kp]
        #to_concat_val_kp = [X_clustered_val_kp, X_val_kp, mu_val_kp, y_val_kp]

        #df_cleansed_train_kp = pd.concat(to_concat_train_kp, axis=1)
        #df_cleansed_val_kp = pd.concat(to_concat_val_kp, axis=1)
        #df_centroids_train_kp.to_csv(TRAIN_CENTROIDS_KP_DATA_FILEPATH, index=False)
        #df_cleansed_train_kp.to_csv(TRAIN_CLEANSED_KP_DATA_FILEPATH, index=False)
        #df_cleansed_val_kp.to_csv(VALIDATE_CLEANSED_KP_DATA_FILEPATH, index=False)

        # PCA
        print('applying pca')
        # remove columns not relevant for pca or clustering
        X_meta_train = X_pca_train[COLS_NOT_FOR_CLUSTERING].copy().astype(int)
        X_meta_val = X_pca_val[COLS_NOT_FOR_CLUSTERING].copy().astype(int)

        X_pca_train = X_pca_train.drop(COLS_NOT_FOR_CLUSTERING, axis=1)
        #X_pca_train.to_csv('pca_train_df', index=False)
        X_pca_val = X_pca_val.drop(COLS_NOT_FOR_CLUSTERING, axis=1)
        #X_pca_val.to_csv('pca_val_df', index=False)
        X_pca_train, X_pca_val  = apply_pca([X_pca_train, X_pca_val])

        # k-means clustering to consturct discrete states
        print('clustering for pca features')
        df_centroids_pca_train, X_pca_clustered_train, X_pca_clustered_val = \
                clustering(X_pca_train, X_pca_val, k=num_states, batch_size=300)

        # stitching up
        print('saving processed pca data')
        to_concat_pca_train = [X_pca_clustered_train, mu_train, X_meta_train, X_pca_train, y_train]
        to_concat_pca_val = [X_pca_clustered_val, mu_val, X_meta_val, X_pca_val, y_val]

        # add one standard deviation stuff
        df_cleansed_pca_train = pd.concat(to_concat_train, axis=1)
        df_cleansed_pca_val = pd.concat(to_concat_val, axis=1)
        df_centroids_pca_train.to_csv(TRAIN_CENTROIDS_PCA_DATA_FILEPATH, index=False)
        df_cleansed_pca_train.to_csv(TRAIN_CLEANSED_PCA_DATA_FILEPATH, index=False)
        df_cleansed_pca_val.to_csv(VALIDATE_CLEANSED_PCA_DATA_FILEPATH, index=False)

    assert not df_cleansed_train.isnull().values.any(), "there's null values in df_cleansed_train"
    assert not df_cleansed_val.isnull().values.any(), "there's null values in df_cleansed_val"
    assert not df_centroids_train.isnull().values.any(), "there's null values in df_centroids_train"

    assert not df_cleansed_pca_train.isnull().values.any(), "there's null values in df_cleansed_pca_train"
    assert not df_cleansed_pca_val.isnull().values.any(), "there's null values in df_cleansed_pca_val"
    assert not df_centroids_pca_train.isnull().values.any(), "there's null values in df_centroids_pca_train"


    #assert not df_cleansed_train_kp.isnull().values.any(), "there's null values in df_cleansed_train_kp"
    #assert not df_cleansed_val_kp.isnull().values.any(), "there's null values in df_cleansed_val_kp"
    #assert not df_centroids_train_kp.isnull().values.any(), "there's null values in df_centroids_train_kp"

    # we don't load full data
    # if need be, it's easy to add them
    df_full = pd.concat([df_cleansed_train, df_cleansed_val], axis=0, ignore_index=True)
    #df_full_kp = pd.concat([df_cleansed_train_kp, df_cleansed_val_kp], axis=0, ignore_index=True)
    df_pca_full = pd.concat([df_cleansed_pca_train, df_cleansed_pca_val], axis=0, ignore_index=True)
    data = {
        'kmeans': {
            'train': df_cleansed_train,
            'val' : df_cleansed_val,
            'centroids': df_centroids_train,
            'full': df_full
           },
        'kprototype': {
            #'train': df_cleansed_train_kp,
            #'val' : df_cleansed_val_kp,
            #'centroids': df_centroids_train_kp,
            #'full': df_full_kp
        },
        'kmeans_pca': {
            'train': df_cleansed_pca_train,
            'val' : df_cleansed_pca_val,
            'centroids': df_centroids_pca_train,
            'full': df_pca_full
        },
        'kprototype_pca': {
            # @todo
        }
    }

    return data

def _load_data(path):
    df = pd.read_csv(path)
    valid_int_cols = list(set(df.columns) & set(INTEGER_COLS))
    df[valid_int_cols].astype(np.int)
    return df

def initialize_save_data_folder():
    date = datetime.datetime.now().strftime('%Y_%m_%d')
    save_path = DATA_PATH + date + '/'
    try:
        if not os.path.exists(save_path):
            os.makedirs(save_path)
            if not os.path.exists(save_path + IMG_PATH):
                os.makedirs(save_path + IMG_PATH)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise Exception('could not initialize save data folder')
    return save_path

def extract_trajectories(df, num_states, trajectory_filepath, action_column='action'):
    # check if df for binary variables are okay
    if os.path.isfile(trajectory_filepath):
        trajectories = np.load(trajectory_filepath)
    else:
        print('extract trajectories')
        trajectories = _extract_trajectories(df, num_states, action_column)
        np.save(trajectory_filepath, trajectories)
    trajectories = trajectories.astype(np.int)
    return trajectories

def _extract_trajectories(df, num_states, action_column):
    '''
    a few strong assumptions are made here.
    1. we consider those who died in 90 days but not in hopsital to have the same status as alive. hence we give reward of one. Worry not. we can change back. this assumption was to be made to account for uncertainty in the cause of dealth after leaving the hospital
    '''
    cols = ['icustayid', 's', 'a', 'r', 'new_s']
    df = df.sort_values(['icustayid', 'bloc'])
    groups = df.groupby('icustayid')
    trajectories = pd.DataFrame(np.zeros((df.shape[0], len(cols))), columns=cols)
    trajectories.loc[:, 'icustayid'] = df['icustayid']
    trajectories.loc[:, 's'] = df['state']
    trajectories.loc[:, 'a'] = df[action_column]

    # reward function
    DEFAULT_REWARD = 0
    trajectories.loc[:, 'r'] = DEFAULT_REWARD
    terminal_steps = groups.tail(1).index
    is_terminal = df.isin(df.iloc[terminal_steps, :]).iloc[:, 0]
    died_in_hosp = df[OUTCOMES[0]] == 1
    died_in_90d = df[OUTCOMES[1]] == 1
    # reward for those who survived (order matters)
    trajectories.loc[is_terminal, 'r'] = 1
    trajectories.loc[is_terminal & died_in_hosp, 'r'] = -1

    # TODO: vectorize this
    new_s = pd.Series([])
    for name, g in groups:
        # add three imaginary states
        # to simplify, we use died_in_hosp_only
        if np.any(g['died_in_hosp'] == 1):
            terminal_marker = TERMINAL_STATE_DEAD
        else:
            # survived
            terminal_marker = TERMINAL_STATE_ALIVE
        new_s_sequence = g['state'].shift(-1)
        new_s_sequence.iloc[-1] = terminal_marker
        new_s = pd.concat([new_s, new_s_sequence])
    trajectories.loc[:, 'new_s'] = new_s.astype(np.int)

    return trajectories.as_matrix()

def normalize_data(df_train, df_val, normalize_categorical=True):
    # divide cols: numerical, categorical, text data
    # logarithimic scale
    df_train = df_train.copy()
    df_val = df_val.copy()
    if normalize_categorical:
        cols = COLS_TO_BE_NORMALIZED_PLUS
    else:
        # exclude from above gender readmission
        # elixhauser', 'SOFA', 'SIRS', 'GCS', 'Shock_Index
        cols = COLS_TO_BE_NORMALIZED
    norm_means_train = np.mean(df_train[cols], axis=0)
    norm_stds_train = np.std(df_train[cols], axis=0)
    df_train[cols] -= norm_means_train
    df_train[cols] /= norm_stds_train
    df_val[cols] -= norm_means_train
    df_val[cols] /= norm_stds_train
    return df_train, df_val

def correct_data(df_train, df_val):
    '''
    we correct both train and val data
    based on stats derived from train data
    '''
    # the logic is hard-coded. could be fixed...
    # TODO: vectorize this
    df_train['sedation'] = df_train['sedation'].clip(0.0)
    df_val['sedation'] = df_val['sedation'].clip(0.0)

    for i, c in enumerate(COLS_TO_BE_LOGGED):
        # ideally correct missing data or obviously wrong values
        stats_train = df_train[c].describe(percentiles=[.01, 0.99])
        min_val_train = stats_train['1%']
        max_val_train = stats_train['99%']
        df_train[c] = df_train[c].clip(min_val_train, max_val_train)
        df_val[c] = df_val[c].clip(min_val_train, max_val_train)

    # TODO: why another loop? I don't remember...
    for i, c in enumerate(COLS_TO_BE_LOGGED):
        # k means clustering assumes vars are normally distributed
        # to control the effect of outliers or a certain var
        # we artificially make the vars look more normal
        df_train[c] = np.log(df_train[c])
        finite_min = df_train[c][np.isfinite(df_train[c])].min()
        df_train[c] = df_train[c].clip(finite_min)
        #stats = df_train[c].describe()
        #sns.distplot(df[c], color=palette[i])
        #plt.show()
        # if we used train finite min, there may be numerical issue
        df_val[c] = np.log(df_val[c])
        finite_min = df_val[c][np.isfinite(df_val[c])].min()
        df_val[c] = df_val[c].clip(finite_min)
    return df_train, df_val


def separate_X_mu_y(df_train, df_val, cols=None):
    num_bins = 5
    mu_train = df_train[INTERVENTIONS]
    iv_train = mu_train['input_4hourly_tev']
    vaso_train = mu_train['median_dose_vaso']
    mu_val = df_val[INTERVENTIONS]
    iv_val = mu_val['input_4hourly_tev']
    vaso_val = mu_val['median_dose_vaso']

    iv_bin_edges, vaso_bin_edges = get_action_discretization_rules(iv_train, vaso_train)
    bins_vaso_train = discretize_actions(vaso_train, vaso_bin_edges)
    bins_iv_train = discretize_actions(iv_train, iv_bin_edges)
    bins_vaso_val = discretize_actions(vaso_val, vaso_bin_edges)
    bins_iv_val = discretize_actions(iv_val, iv_bin_edges)

    mu_train['action'] = bins_vaso_train * num_bins + bins_iv_train
    mu_train['action_vaso'] = bins_vaso_train
    mu_train['action_iv'] = bins_iv_train

    mu_val['action'] = bins_vaso_val * num_bins + bins_iv_val
    mu_val['action_vaso'] = bins_vaso_val
    mu_val['action_iv'] = bins_iv_val
    y_train = df_train[OUTCOMES].astype(int)
    y_val = df_val[OUTCOMES].astype(int)

    if cols is None:
        default_cols = set(ALL_VALUES) - set(OUTCOMES)
        X_train = df_train[list(default_cols)]
        X_val = df_val[list(default_cols)]
    else:
        observation_cols = set(cols) - set(OUTCOMES) - set(INTERVENTIONS)
        X_train = df_train[list(observation_cols)]
        X_val = df_val[list(observation_cols)]
    return X_train, mu_train, y_train, X_val, mu_val, y_val


def get_sd_away_bins(df):
    if os.path.isfile(STD_BINS_IV_FILEPATH) and os.path.isfile(STD_BINS_VASO_FILEPATH):
        df_iv = pd.read_csv(STD_BINS_IV_FILEPATH)
        df_vaso = pd.read_csv(STD_BINS_VASO_FILEPATH)
    else:

        # bin a data point one s.d. away to the left from the observed  data point
        # additional analysis to account for binning error
        state_groups = df.groupby(['state'])
        # per state standard deviation
        # find std in the original feature space before binning
        iv_sd = state_groups['input_4hourly_tev'].std()
        vaso_sd = state_groups['median_dose_vaso'].std()
        # find mode in the original feature space before binning
        iv_mode = state_groups['input_4hourly_tev'].agg(lambda x:x.value_counts().index[0])
        vaso_mode = state_groups['median_dose_vaso'].agg(lambda x:x.value_counts().index[0])
        # find binning criteria
        iv_bin_edges, vaso_bin_edges = get_action_discretization_rules(df['input_4hourly_tev'],
                                                                       df['median_dose_vaso'])
        # find std bins
        vaso_low = df['median_dose_vaso'].min()
        vaso_high = df['median_dose_vaso'].max()
        iv_low = df['input_4hourly_tev'].min()
        iv_high = df['input_4hourly_tev'].max()

        bin_vaso_sd_l, bin_vaso_mode, bin_vaso_sd_r = _get_sd_away_bins(vaso_mode,
                                                                        vaso_sd,
                                                                        vaso_low,
                                                                        vaso_high,
                                                                        vaso_bin_edges)

        bin_iv_sd_l, bin_iv_mode, bin_iv_sd_r = _get_sd_away_bins(iv_mode,
                                                                  iv_sd,
                                                                  iv_low,
                                                                  iv_high,
                                                                  iv_bin_edges)
        bin_vaso_sd_l.name = 'action_vaso_sd_left'
        bin_vaso_mode.name = 'action_vaso'
        bin_vaso_sd_r.name = 'action_vaso_sd_right'

        bin_iv_sd_l.name = 'action_iv_sd_left'
        bin_iv_mode.name = 'action_iv'
        bin_iv_sd_r.name = 'action_iv_sd_right'
        df_vaso = pd.concat([bin_vaso_sd_l, bin_vaso_mode, bin_vaso_sd_r], axis=1)
        df_iv = pd.concat([bin_iv_sd_l, bin_iv_mode, bin_iv_sd_r], axis=1)

        num_bins = 5
        df_iv.loc[df_iv['action_iv_sd_left'] != df_iv['action_iv'], 'action_iv_sd_left'] = (df_iv['action_iv'].copy() - 1).clip(0, num_bins-1)
        df_iv.loc[df_iv['action_iv_sd_right'] != df_iv['action_iv'], 'action_iv_sd_right'] = (df_iv['action_iv'].copy() + 1).clip(0, num_bins-1)
        df_vaso.loc[df_vaso['action_vaso_sd_left'] != df_vaso['action_vaso'], 'action_vaso_sd_left'] = (df_vaso['action_vaso'].copy() - 1).clip(0, num_bins-1)
        df_vaso.loc[df_vaso['action_vaso_sd_right'] != df_vaso['action_vaso'], 'action_vaso_sd_right'] = (df_vaso['action_vaso'].copy() + 1).clip(0, num_bins-1)

        df_vaso.to_csv(STD_BINS_VASO_FILEPATH, index=False)
        df_iv.to_csv(STD_BINS_IV_FILEPATH, index=False)
    return df_vaso, df_iv


def _get_sd_away_bins(df_mode, df_sd, low, high, bin_edges):
    '''
    binning iv, vaso
    '''
    df_sd_l = (df_mode - df_sd).clip(low, high)
    df_sd_r = (df_mode + df_sd).clip(low, high)
    l = discretize_actions(df_sd_l, bin_edges)
    m = discretize_actions(df_mode, bin_edges)
    r = discretize_actions(df_sd_r, bin_edges)
    return l, m, r


def apply_pca(dataframes, n_components=None):
    if n_components is None:
        n_components = len(dataframes[0].columns)
    pca = PCA(n_components=n_components)
    # fit on the df_train
    pca.fit(dataframes[0])
    pca_results = []
    for df in dataframes:
        X_pca = pd.DataFrame(pca.transform(df), columns=df.columns)
        pca_results.append(X_pca)
    return pca_results


def inverse_pca(df, n_components=None):
    if n_components is None:
        n_components = len(df.columns)
    p = PCA(n_components=n_components)
    X = p.fit_transform(df)
    return p.inverse_transform(X)

def clustering(X_train, X_val, k=750, batch_size=300, minibatch=True):
    if minibatch:
        # pick only numerical columns that make sense
        mbk = MiniBatchKMeans(n_clusters=k, batch_size=batch_size, init_size=k*3)
    else:
        mbk = KMeans(n_clusters=k, random_state=0, n_jobs=7)

    # fit only on train
    mbk.fit(X_train)
    X_centroids_train = mbk.cluster_centers_
    df_centroids_train = pd.DataFrame(X_centroids_train, columns=X_train.columns)

    X_clustered_train = pd.Series(mbk.predict(X_train), name='state')
    X_clustered_val = pd.Series(mbk.predict(X_val), name='state')
    return df_centroids_train, X_clustered_train, X_clustered_val

def clustering_kp(X_train, X_val, num_states, init_method='Cao'):
    # @refactor
    # preprocessing to keep things orderly for kp method

    cat_cols = PSEUDO_OBSERVATIONS + ['elixhauser', 'SOFA', 'SIRS', 'gender', 're_admission']
    cols = X_train.columns.tolist()
    num_cols = list(set(cols) - set(cat_cols))
    # change the order
    X_train = X_train[num_cols + cat_cols]
    X_train[cat_cols] = X_train[cat_cols].astype(int)
    # number of data points
    N = len(X_train.index)
    # number of clusters
    K = num_states
    # num of features
    M = len(X_train.columns.tolist())
    # num of cat features
    MN = len(cat_cols)
    # init_method cao or huang
    kp = KPrototypes(n_clusters=K, max_iter=200, init=init_method, verbose=2)
    # fit only on train
    kp.fit(X_train, categorical=list(range(M - MN, M)))
    # @todo check if it's decoded version to use
    X_centroids_train = kp.cluster_centroids_[0]
    df_centroids_train = pd.DataFrame(X_centroids_train, columns=X_train.columns)

    clusters_train = kp.predict(X_train, categorical=list(range(M - MN, M)))
    clusters_val= kp.predict(X_val, categorical=list(range(M - MN, M)))
    X_clustered_train = pd.Series(clusters_train, name='state')
    X_clustered_val = pd.Series(clusters_val, name='state')
    import pdb;pdb.set_trace()

    return df_centroids_train, X_clustered_train, X_clustered_val

def get_action_discretization_rules(
        input_4hourly__sequence__continuous,
        median_dose_vaso__sequence__continuous,
        bins_num = 5):
    # IV fluids discretization
    input_4hourly__sequence__continuous__no_zeros = input_4hourly__sequence__continuous[ \
        input_4hourly__sequence__continuous > 0]
    input_4hourly__sequence__discretized__no_zeros, input_4hourly__bin_bounds = \
        pd.qcut( input_4hourly__sequence__continuous__no_zeros, \
                 bins_num - 1, labels = False, retbins = True)
    input_4hourly__sequence__discretized = \
        (input_4hourly__sequence__continuous > 0).astype(int)
    input_4hourly__sequence__discretized[ input_4hourly__sequence__discretized == 1 ] = \
        input_4hourly__sequence__discretized__no_zeros + 1
    # Vaopressors discretization
    median_dose_vaso__sequence__continuous__no_zeros = median_dose_vaso__sequence__continuous[ \
        median_dose_vaso__sequence__continuous > 0]
    median_dose_vaso__sequence__discretized__no_zeros, median_dose_vaso__bin_bounds = \
        pd.qcut( median_dose_vaso__sequence__continuous__no_zeros, \
                 bins_num - 1, labels = False, retbins = True)
    median_dose_vaso__sequence__discretized = \
        (median_dose_vaso__sequence__continuous > 0).astype(int)
    median_dose_vaso__sequence__discretized[ median_dose_vaso__sequence__discretized == 1 ] = \
        median_dose_vaso__sequence__discretized__no_zeros + 1

    # we need this because bounds for validate data may not match
    input_4hourly__bin_bounds = np.insert(input_4hourly__bin_bounds, 0, 0.0)
    input_4hourly__bin_bounds[-1] = np.inf
    median_dose_vaso__bin_bounds = np.insert(median_dose_vaso__bin_bounds, 0, 0.0)
    median_dose_vaso__bin_bounds[-1] = np.inf

    return input_4hourly__bin_bounds, median_dose_vaso__bin_bounds

def discretize_actions(df, bin_edges, num_bins=5):
    bins = pd.cut(df, bin_edges, include_lowest=True, labels=np.arange(num_bins))
    bins = bins.astype(np.int)
    return bins

def is_terminal_state(s):
    return s >= (NUM_STATES - NUM_TERMINAL_STATES)

def compute_terminal_state_reward(s, num_features):
    if s == TERMINAL_STATE_ALIVE:
        return np.sqrt(num_features)
    elif s == TERMINAL_STATE_DEAD:
        return -np.sqrt(num_features)
    else:
        raise Exception('not recognizing this terminal state: '.foramt(s))

def apply_phi_to_centroids(df_cent, df_train, bins=None, as_matrix=False):
    '''
    phi criteria are learned from df_trani
    convert centroid values into quartile-based bins
    create dummy variable so every column is one or zero
    '''
    if bins is None:
        bins = ['min', '25%', '50%', '75%', 'max']
    criteria = df_train.describe().loc[bins]
    # pandas cut does not see to support vectorized version
    binned_columns = []

    for c in df_cent:
        uniq_edges = np.unique(criteria[c].tolist())
        if len(uniq_edges) == 2:
            # it must be binary variables
            # shift the edge to the left a bit
            uniq_edges = uniq_edges - 1e-5
            # add a new edge
            uniq_edges = np.append(uniq_edges, 10000)
            #print(uniq_edges)
            labels = np.arange(2, dtype=np.int)
            #print(labels)
        else:
            labels = np.arange(len(uniq_edges) - 1, dtype=np.int)
        bins = pd.cut(df_cent[c], uniq_edges, include_lowest=True, retbins=True, labels=labels)[0]
        bins.astype(int)
        binned_columns.append(bins)

    df_binned = pd.concat(binned_columns, axis=1, ignore_index=True)
    df_binned.columns = df_cent.columns
    df_phi = pd.get_dummies(df_binned)
    if as_matrix:
        return df_phi.as_matrix()
    else:
        return df_phi

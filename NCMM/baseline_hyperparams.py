ARCHITECTURE = 'lstm'
# training parameters
NUM_EPOCHS = 300
APG_SWEEPS = 1
SAMPLE_SIZE = 10
BATCH_SIZE = 20
LR =  1e-4

K = 4
D = 2
NUM_HIDDEN_STATE = 32
NUM_HIDDEN_ANGLE = 32
NUM_HIDDEN_DEC = 32
RECON_SIGMA =  0.3
if ARCHITECTURE == 'lstm':
    NUM_HIDDEN_LSTM = 32
    NUM_LAYERS = 2
    model_params = (K, D, NUM_HIDDEN_LSTM, BATCH_SIZE, SAMPLE_SIZE, NUM_LAYERS, NUM_HIDDEN_STATE, NUM_HIDDEN_ANGLE, NUM_HIDDEN_DEC, RECON_SIGMA)
else:
    NUM_HIDDEN_GLOBAL = 32
    NUM_NSS = 8
    model_params = (K, D, NUM_HIDDEN_GLOBAL, NUM_NSS, NUM_HIDDEN_STATE, NUM_HIDDEN_ANGLE, NUM_HIDDEN_DEC, RECON_SIGMA)
MODEL_NAME = 'baseline-%s' % ARCHITECTURE
MODEL_VERSION = 'ncmm-%s-%dsamples-%.4flr' % (MODEL_NAME, SAMPLE_SIZE, LR)
# LOAD_VERSION = 'ncmm-10samples-0.0005lr'
print('inference method:%s, epochs:%s, sample size:%s, batch size:%s, learning rate:%s' % (MODEL_NAME, NUM_EPOCHS, SAMPLE_SIZE, BATCH_SIZE, LR))

# data_path = data_dir + "ncmm/rings_%d" % N*K
#
# Data = torch.from_numpy(np.load(data_path + '/ob_%d.npy' % (N * K))).float()

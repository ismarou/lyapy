from keras.layers import Add, Dot, Input
from keras.models import Model
from matplotlib.animation import FuncAnimation
from matplotlib.pyplot import figure, grid, legend, plot, show, subplot, suptitle, title
from numpy import append, argsort, array, concatenate, cumsum, dot, linspace, max, min, reshape, sign, split, zeros
from numpy.linalg import norm, lstsq
from numpy.random import rand
from scipy.io import loadmat

from ..controllers import PDController, SegwayController
from ..systems import Segway
from ..learning import constant_controller, differentiator, evaluator, interpolate, discrete_random_controller, sum_controller, two_layer_nn, principal_scaling_connect_models, principal_scaling_augmenting_controller, weighted_controller

n, m = 4, 1

m_b_hat, m_w_hat, J_w_hat, c_2_hat, B_2_hat, R_hat, K_hat, r_hat, g, h_hat, m_p_hat = 20.42, 2.539, 0.063, -0.029, 0.578, 0.8796, 1.229, 0.195, 9.81, 0.56, 3.8
param_hats = array([m_b_hat, m_w_hat, J_w_hat, c_2_hat, B_2_hat, R_hat, K_hat, r_hat, h_hat, m_p_hat])
delta = 0.2
m_b, m_w, J_w, c_2, B_2, R, K, r, h, m_p = (2 * delta * rand(len(param_hats)) + 1 - delta) * param_hats

segway_true = Segway(m_b, m_w, J_w, c_2, B_2, R, K, r, g, h, m_p)
segway_est = Segway(m_b_hat, m_w_hat, J_w_hat, c_2_hat, B_2_hat, R_hat, K_hat, r_hat, g, h_hat, m_p_hat)

K_qp = array([1, 1])
K_pd = array([[0, -100, 0, -1]])

res = loadmat('./lyapy/trajectories/segway.mat')
x_ds, t_ds, u_ds = res['X_d'], res['T_d'][:, 0], res['U_d']

r, r_dot, r_ddot = interpolate(t_ds, x_ds[:, 0:2], x_ds[:, 2:])
r_qp = lambda t: r(t)[1]
r_dot_qp = lambda t: r_dot(t)[1]
r_ddot_qp = lambda t: r_ddot(t)[1]

qp_controller = SegwayController(segway_est, K_qp, r_qp, r_dot_qp, r_ddot_qp)
true_controller = SegwayController(segway_true, K_qp, r_qp, r_dot_qp, r_ddot_qp)
pd_controller = PDController(K_pd, r, r_dot)

x_0 = array([2, 0, 0, 0])
t_span = [0, 5]
dt = 1e-3
t_eval = [step * dt for step in range((t_span[-1] - t_span[0]) * int(1 / dt))]

t_qps, x_qps = segway_true.simulate(qp_controller.u, x_0, t_eval)
width = 0.1
reps = 10
u_pd = sum_controller([pd_controller.u, discrete_random_controller(pd_controller.u, m, width, t_eval, reps)])
t_pds, x_pds = segway_true.simulate(u_pd, x_0, t_eval)

u_qps = array([qp_controller.u(x, t) for x, t in zip(x_qps, t_qps)])
u_pds = array([u_pd(x, t) for x, t in zip(x_pds, t_pds)])

int_u_qps = cumsum(abs(u_qps)) * dt
int_u_pds = cumsum(abs(u_pds)) * dt

figure()
suptitle('QP Controller', fontsize=16)

subplot(2, 2, 1)
plot(t_ds, x_ds[:, 0], '--', linewidth=2)
plot(t_qps, x_qps[:, 0], linewidth=2)
grid()
legend(['$x_d$', '$x$'], fontsize=16)

subplot(2, 2, 2)
plot(t_ds, x_ds[:, 1], '--', linewidth=2)
plot(t_qps, x_qps[:, 1], linewidth=2)
grid()
legend(['$\\theta_d$', '$\\theta$'], fontsize=16)

subplot(2, 2, 3)
plot(t_ds, x_ds[:, 2], '--', linewidth=2)
plot(t_qps, x_qps[:, 2], linewidth=2)
grid()
legend(['$\\dot{x}_d$', '$\\dot{x}$'], fontsize=16)

subplot(2, 2, 4)
plot(t_ds, x_ds[:, 3], '--', linewidth=2)
plot(t_qps, x_qps[:, 3], linewidth=2)
grid()
legend(['$\\dot{\\theta}_d$', '$\\dot{\\theta}$'], fontsize=16)

figure()
suptitle('PD Controller', fontsize=16)

subplot(2, 2, 1)
plot(t_ds, x_ds[:, 0], '--', linewidth=2)
plot(t_pds, x_pds[:, 0], linewidth=2)
grid()
legend(['$x_d$', '$x$'], fontsize=16)

subplot(2, 2, 2)
plot(t_ds, x_ds[:, 1], '--', linewidth=2)
plot(t_pds, x_pds[:, 1], linewidth=2)
grid()
legend(['$\\theta_d$', '$\\theta$'], fontsize=16)

subplot(2, 2, 3)
plot(t_ds, x_ds[:, 2], '--', linewidth=2)
plot(t_pds, x_pds[:, 2], linewidth=2)
grid()
legend(['$\\dot{x}_d$', '$\\dot{x}$'], fontsize=16)

subplot(2, 2, 4)
plot(t_ds, x_ds[:, 3], '--', linewidth=2)
plot(t_pds, x_pds[:, 3], linewidth=2)
grid()
legend(['$\\dot{\\theta}_d$', '$\\dot{\\theta}$'], fontsize=16)

figure()

subplot(2, 1, 1)
title('Control', fontsize=16)
plot(t_pds, u_pds, '--', linewidth=2)
plot(t_qps, u_qps, linewidth=2)
grid()
legend(['$u_{PD}$', '$u_{QP}$'], fontsize=16)


subplot(2, 1, 2)
title('Control integral', fontsize=16)
plot(t_pds, int_u_pds, '--', linewidth=2)
plot(t_qps, int_u_qps, linewidth=2)
grid()
legend(['$u_{PD}$', '$u_{QP}$'], fontsize=16)

d_hidden = 50

L = 3
diff = differentiator(L, dt)

num_episodes = 10
weights = linspace(0, 1, num_episodes + 1)[:-1]
num_trajectories = 1
num_pre_train_epochs = 1000
num_epochs = 1000
subsample_rate = reps

# principal_scaling = lambda x, t: norm(qp_controller.dVdx(x, t)[2:])
principal_scaling = lambda x, t: qp_controller.dVdx(x, t)[-1]
alpha = 1 / qp_controller.lambda_1

dVdx_episodes = zeros((0, n))
g_episodes = zeros((0, n, m))
principal_scaling_episodes = zeros((0,))
x_episodes = zeros((0, n))
u_c_episodes = zeros((0, m))
u_l_episodes = zeros((0, m))
V_r_dot_episodes = zeros((0,))
t_episodes = zeros((0,))

window = 5

x_lst_sq_episodes = zeros((0, n))
a_lst_sq_episodes = zeros((0, m))
b_lst_sq_episodes = zeros((0, 1))
principal_scaling_lst_sq_episodes = zeros((0,))
t_lst_sq_episodes = zeros((0,))

u_aug = constant_controller(zeros((m,)))

for episode, weight in enumerate(weights):
    print('EPISODE', episode + 1)

    a = two_layer_nn(n, d_hidden, (m,))
    b = two_layer_nn(n, d_hidden, (1,))
    model = principal_scaling_connect_models(a, b)

    a.compile('adam', 'mean_absolute_error')
    b.compile('adam', 'mean_absolute_error')
    model.compile('adam', 'mean_squared_error')

    u_c = sum_controller([pd_controller.u, weighted_controller(weight, u_aug)])
    u_ls = [discrete_random_controller(pd_controller.u, m, width, t_eval, reps) for _ in range(num_trajectories)]
    us = [sum_controller([u_c, u_l]) for u_l in u_ls]

    sols = [segway_true.simulate(u, x_0, t_eval) for u in us]

    Vs = [array([qp_controller.V(x, t) for x, t in zip(xs, ts)]) for ts, xs in sols]
    V_dots = [diff(Vs)[::subsample_rate] for Vs in Vs]

    half_L = (L - 1) // 2
    xs = [xs[half_L:-half_L:subsample_rate] for _, xs in sols]
    ts = [ts[half_L:-half_L:subsample_rate] for ts, _ in sols]
    u_cs = [array([u_c(x, t) for x, t in zip(xs, ts)]) for xs, ts in zip(xs, ts)]
    u_ls = [array([u_l(x, t) for x, t in zip(xs, ts)]) for xs, ts, u_l in zip(xs, ts, u_ls)]

    V_d_dots = [array([qp_controller.dV(x, u_c, t) for x, u_c, t in zip(xs, u_cs, ts)]) for xs, u_cs, ts in zip(xs, u_cs, ts)]
    V_r_dots = [V_dots - V_d_dots for V_dots, V_d_dots in zip(V_dots, V_d_dots)]

    dVdxs = [array([qp_controller.dVdx(x, t) for x, t in zip(xs, ts)]) for xs, ts in zip(xs, ts)]
    principal_scalings = [array([principal_scaling(x, t) for x, t in zip(xs, ts)]) for xs, ts in zip(xs, ts)]
    # principal_scalings = [array([norm(dVdx[2:]) for dVdx in dVdxs]) for dVdxs in dVdxs]

    A_lst_sqs = [array([principal_scaling * append(u_c + u_l, 1) for principal_scaling, u_c, u_l in zip(principal_scalings, u_cs, u_ls)]) for principal_scalings, u_cs, u_ls in zip(principal_scalings, u_cs, u_ls)]
    b_lst_sqs = [array([V_r_dot - dot(qp_controller.LgV(x, t), u_l) for V_r_dot, x, u_l, t in zip(V_r_dots, xs, u_ls, ts)]) for V_r_dots, xs, u_ls, ts in zip(V_r_dots, xs, u_ls, ts)]

    w_lst_sqs = concatenate([array([lstsq(A_lst_sqs[idx:idx+window], b_lst_sqs[idx:idx+window], rcond=None)[0] for idx in range(len(A_lst_sqs) - window + 1)]) for A_lst_sqs, b_lst_sqs in zip(A_lst_sqs, b_lst_sqs)])
    a_lst_sqs = w_lst_sqs[:, :-1]
    b_lst_sqs = w_lst_sqs[:, -1:]

    half_window = (window - 1) // 2
    x_lst_sqs = concatenate([xs[half_window:-half_window] for xs in xs])
    principal_scaling_lst_sqs = concatenate([principal_scalings[half_window:-half_window] for principal_scalings in principal_scalings])
    t_lst_sqs = concatenate([ts[half_window:-half_window] for ts in ts])

    x_lst_sq_episodes = concatenate([x_lst_sq_episodes, x_lst_sqs])
    a_lst_sq_episodes = concatenate([a_lst_sq_episodes, a_lst_sqs])
    b_lst_sq_episodes = concatenate([b_lst_sq_episodes, b_lst_sqs])
    principal_scaling_lst_sq_episodes = concatenate([principal_scaling_lst_sq_episodes, principal_scaling_lst_sqs])
    t_lst_sq_episodes = concatenate([t_lst_sq_episodes, t_lst_sqs])

    N = len(x_lst_sq_episodes)

    a_pre_trues_dat = array([(true_controller.LgV(x, t) - qp_controller.LgV(x, t)) / principal_scaling for x, t, principal_scaling in zip(x_lst_sq_episodes, t_lst_sq_episodes, principal_scaling_lst_sq_episodes)])
    b_pre_trues_dat = array([(true_controller.LfV(x, t) - qp_controller.LfV(x, t)) / principal_scaling for x, t, principal_scaling in zip(x_lst_sq_episodes, t_lst_sq_episodes, principal_scaling_lst_sq_episodes)])

    # TODO: Fix this, it wrong

    print('Fitting a...')
    # a.fit(x_lst_sq_episodes, a_lst_sq_episodes, epochs=num_pre_train_epochs, batch_size=N)
    a.fit(x_lst_sq_episodes, a_pre_trues_dat, epochs=num_pre_train_epochs, batch_size=N, validation_split=0.2)
    print('Fitting b...')
    # b.fit(x_lst_sq_episodes, b_lst_sq_episodes, epochs=num_pre_train_epochs, batch_size=N)
    b.fit(x_lst_sq_episodes, b_pre_trues_dat, epochs=num_pre_train_epochs, batch_size=N, validation_split=0.2)

    a_w1, a_b1 = a.layers[0].get_weights()
    a_w2, a_b2 = a.layers[2].get_weights()
    b_w1, b_b1 = b.layers[0].get_weights()
    b_w2, b_b2 = b.layers[2].get_weights()

    print('a layer 1')
    print(norm(a_w1, 2), norm(a_b1))
    print('a layer 2')
    print(norm(a_w2, 2), norm(a_b2))
    print('b layer 1')
    print(norm(b_w1, 2), norm(b_b1))
    print('b layer 2')
    print(norm(b_w2, 2), norm(b_b2))


    a_pre_ests = a.predict(x_lst_sq_episodes)
    a_pre_ests = array([principal_scaling * a_est for principal_scaling, a_est in zip(principal_scaling_lst_sq_episodes, a_pre_ests)])
    b_pre_ests = b.predict(x_lst_sq_episodes)[:,0]
    b_pre_ests = array([principal_scaling * b_est for principal_scaling, b_est in zip(principal_scaling_lst_sq_episodes, b_pre_ests)])

    a_pre_trues = array([true_controller.LgV(x, t) - qp_controller.LgV(x, t) for x, t in zip(x_lst_sq_episodes, t_lst_sq_episodes)])
    b_pre_trues = array([true_controller.LfV(x, t) - qp_controller.LfV(x, t) for x, t in zip(x_lst_sq_episodes, t_lst_sq_episodes)])
    a_mse = norm(a_pre_ests - a_pre_trues, 'fro') ** 2 / (2 * N)
    b_mse = norm(b_pre_ests - b_pre_trues) ** 2 / (2 * N)
    print('a_mse', a_mse, 'b_mse', b_mse)

    dVdxs = concatenate(dVdxs)
    principal_scalings = concatenate(principal_scalings)
    xs = concatenate(xs)
    u_cs = concatenate(u_cs)
    u_ls = concatenate(u_ls)
    V_r_dots = concatenate(V_r_dots)

    ts = concatenate(ts)

    gs = array([segway_est.act(x) for x in xs])

    # V_dots = concatenate([diff(V)[::subsample_rate] for V in Vs])
    #
    # half_L = (L - 1) // 2
    # xs = concatenate([xs[half_L:-half_L:subsample_rate] for _, xs in sols])
    # ts = concatenate([ts[half_L:-half_L:subsample_rate] for ts, _ in sols])
    # u_cs = array([u_c(x, t) for x, t in zip(xs, ts)])
    # u_ls = concatenate([array([u_l(x, t) for x, t in zip(xs, ts)])[half_L:-half_L:subsample_rate] for (ts, xs), u_l in zip(sols, u_ls)])
    #
    # V_d_dots = array([qp_controller.dV(x, u_c, t) for x, u_c, t in zip(xs, u_cs, ts)])
    # V_r_dots = V_dots - V_d_dots
    #
    # dVdxs = array([qp_controller.dVdx(x, t) for x, t in zip(xs, ts)])
    # gs = array([segway_est.act(x) for x in xs])
    # principal_scalings = array([norm(dVdx[2:]) for dVdx in dVdxs])

    dVdx_episodes = concatenate([dVdx_episodes, dVdxs])
    g_episodes = concatenate([g_episodes, gs])
    principal_scaling_episodes = concatenate([principal_scaling_episodes, principal_scalings])
    x_episodes = concatenate([x_episodes, xs])
    u_c_episodes = concatenate([u_c_episodes, u_cs])
    u_l_episodes = concatenate([u_l_episodes, u_ls])
    V_r_dot_episodes = concatenate([V_r_dot_episodes, V_r_dots])
    t_episodes = concatenate([t_episodes, ts])

    N = len(x_episodes)

    print('Fitting V_r_dot...')
    # model.fit([dVdx_episodes, g_episodes, principal_scaling_episodes, x_episodes, u_c_episodes, u_l_episodes], V_r_dot_episodes, epochs=num_epochs, batch_size=N)
    model.fit([dVdx_episodes, g_episodes, principal_scaling_episodes, x_episodes, u_c_episodes, u_l_episodes], V_r_dot_episodes, epochs=num_epochs, batch_size=N)

    a_post_ests = a.predict(x_episodes)
    a_post_ests = array([principal_scaling * a_est for principal_scaling, a_est in zip(principal_scaling_episodes, a_post_ests)])
    b_post_ests = b.predict(x_episodes)[:,0]
    b_post_ests = array([principal_scaling * b_est for principal_scaling, b_est in zip(principal_scaling_episodes, b_post_ests)])

    a_post_trues = array([true_controller.LgV(x, t) - qp_controller.LgV(x, t) for x, t in zip(x_episodes, t_episodes)])
    b_post_trues = array([true_controller.LfV(x, t) - qp_controller.LfV(x, t) for x, t in zip(x_episodes, t_episodes)])
    a_mse = norm(a_post_ests - a_post_trues, 'fro') ** 2 / (2 * N)
    b_mse = norm(b_post_ests - b_post_trues) ** 2 / (2 * N)
    print('a_mse', a_mse, 'b_mse', b_mse)

    a_w1, a_b1 = a.layers[0].get_weights()
    a_w2, a_b2 = a.layers[2].get_weights()
    b_w1, b_b1 = b.layers[0].get_weights()
    b_w2, b_b2 = b.layers[2].get_weights()

    print('a layer 1')
    print(norm(a_w1, 2), norm(a_b1))
    print('a layer 2')
    print(norm(a_w2, 2), norm(a_b2))
    print('b layer 1')
    print(norm(b_w1, 2), norm(b_b1))
    print('b layer 2')
    print(norm(b_w2, 2), norm(b_b2))

    C = 1e3
    u_aug = principal_scaling_augmenting_controller(pd_controller.u, qp_controller.V, qp_controller.LfV, qp_controller.LgV, qp_controller.dV, principal_scaling, a, b, C, alpha)

a_lst_sq_episodes = array([a_lst_sq * principal_scaling for a_lst_sq, principal_scaling in zip(a_lst_sq_episodes, principal_scaling_lst_sq_episodes)])
b_lst_sq_episodes = array([b_lst_sq * principal_scaling for b_lst_sq, principal_scaling in zip(b_lst_sq_episodes, principal_scaling_lst_sq_episodes)])

figure()
suptitle('$a$ and $b$ least squares estimates', fontsize=16)

subplot(2, 1, 1)
title('a')
plot(a_lst_sq_episodes)
plot(a_pre_trues, '--')
grid()

subplot(2, 1, 2)
title('b')
plot(b_lst_sq_episodes)
plot(b_pre_trues, '--')
grid()

figure()
suptitle('$a$ and $b$ pretrained estimates', fontsize=16)

subplot(2, 1, 1)
title('a')
plot(a_pre_ests)
plot(a_pre_trues, '--')
grid()

subplot(2, 1, 2)
title('b')
plot(b_pre_ests)
plot(b_pre_trues, '--')
grid()


figure()
suptitle('Debug', fontsize=16)

subplot(2, 1, 1)
title('a')
plot(a_pre_ests)
plot(a_pre_trues_dat, '--')
grid()

subplot(2, 1, 2)
title('b')
plot(b_pre_ests)
plot(b_pre_trues_dat, '--')
grid()


figure()
suptitle('$a$ and $b$ trained estimates', fontsize=16)

subplot(2, 1, 1)
title('a')
plot(a_post_ests)
plot(a_post_trues, '--')
grid()

subplot(2, 1, 2)
title('b')
plot(b_post_ests)
plot(b_post_trues, '--')
grid()

u = sum_controller([pd_controller.u, u_aug])

ts, xs = segway_true.simulate(u, x_0, t_eval)

figure()
suptitle('Augmented Controller', fontsize=16)

subplot(2, 2, 1)
plot(t_ds, x_ds[:, 0], '--', linewidth=2)
plot(ts, xs[:, 0], linewidth=2)
grid()
legend(['$x_d$', '$x$'], fontsize=16)

subplot(2, 2, 2)
plot(t_ds, x_ds[:, 1], '--', linewidth=2)
plot(ts, xs[:, 1], linewidth=2)
grid()
legend(['$\\theta_d$', '$\\theta$'], fontsize=16)

subplot(2, 2, 3)
plot(t_ds, x_ds[:, 2], '--', linewidth=2)
plot(ts, xs[:, 2], linewidth=2)
grid()
legend(['$\\dot{x}_d$', '$\\dot{x}$'], fontsize=16)

subplot(2, 2, 4)
plot(t_ds, x_ds[:, 3], '--', linewidth=2)
plot(ts, xs[:, 3], linewidth=2)
grid()
legend(['$\\dot{\\theta}_d$', '$\\dot{\\theta}$'], fontsize=16)

def V_r_dot_true(x, u_c, u_l, t):
    return true_controller.dV(x, u_c + u_l, t) - qp_controller.dV(x, u_c, t)

V_r_dot_true_episodes = array([V_r_dot_true(x, u_c, u_l, t) for x, u_c, u_l, t in zip(x_episodes, u_c_episodes, u_l_episodes, t_episodes)])

figure()
title('Derivative Estimation', fontsize=16)
plot(V_r_dot_episodes, linewidth=2)
plot(V_r_dot_true_episodes, '--', linewidth=2)
grid()
legend(['Estimated', 'Truth'], fontsize=16)

us = array([u(x, t) for x, t in zip(xs, ts)])
u_trues = array([true_controller.u(x, t) for x, t in zip(xs, ts)])

figure()
title('Controller comparison', fontsize=16)
plot(ts, us, linewidth=2)
plot(ts, u_trues, linewidth=2)
grid()
legend(['Augmented', 'Perfect'], fontsize=16)

show()

# a_errs = a_ests - a_trues
# us = u_c_episodes + u_l_episodes
# b_errs = b_ests - b_trues
# loss_uppers = array([1 / 2 * (principal_scaling * ( abs(dot(a_err, u)) + abs(b_err) )) ** 2 for principal_scaling, a_err, u, b_err in zip(principal_scaling_episodes, a_errs, us, b_errs)])
#
# num_tests = 10
# loss_upper_idxs = argsort(loss_uppers)[-1:-num_tests-1:-1]
# x_errs = x_episodes[loss_upper_idxs]
#
# def find_closest_idxs(x_0, xs, num_closest_points):
#     dists = [norm(x - x_0) for x in xs]
#     dist_idxs = argsort(dists)[1:num_closest_points+1]
#     return dist_idxs
#
# num_closest_points = 2
# closest_idxs = [find_closest_idxs(x_err, x_episodes, num_closest_points) for x_err in x_errs]
#
# lst_sq_idxs = [append(closest_idx, loss_upper_idx) for loss_upper_idx, closest_idx in zip(loss_upper_idxs, closest_idxs)]
# x_lst_sqs = [x_episodes[lst_sq_idx] for lst_sq_idx in lst_sq_idxs]
# principal_scaling_lst_sqs = [principal_scaling_episodes[lst_sq_idx] for lst_sq_idx in lst_sq_idxs]
# u_c_lst_sqs = [u_c_episodes[lst_sq_idx] for lst_sq_idx in lst_sq_idxs]
# u_l_lst_sqs = [u_l_episodes[lst_sq_idx] for lst_sq_idx in lst_sq_idxs]
# V_r_dot_lst_sqs = [V_r_dot_episodes[lst_sq_idx] for lst_sq_idx in lst_sq_idxs]
# dVdx_lst_sqs = [dVdx_episodes[lst_sq_idx] for lst_sq_idx in lst_sq_idxs]
# g_lst_sqs = [array([segway_est.act(x) for x in xs]) for xs in x_lst_sqs]
# t_lst_sqs = [t_episodes[lst_sq_idx] for lst_sq_idx in lst_sq_idxs]
# # a_true_lst_sqs = [a_trues[lst_sq_idx] for lst_sq_idx in lst_sq_idxs]
# # b_true_lst_sqs = [b_trues[lst_sq_idx] for lst_sq_idx in lst_sq_idxs]
#
# A_lst_sqs = [array([principal_scaling * append(u_c + u_l, 1) for principal_scaling, u_c, u_l in zip(principal_scalings, u_cs, u_ls)]) for principal_scalings, u_cs, u_ls in zip(principal_scaling_lst_sqs, u_c_lst_sqs, u_l_lst_sqs)]
#
# b_lst_sq_wrongs = [array([V_r_dot - dot(dVdx, dot(g, u_l)) for V_r_dot, dVdx, g, u_l in zip(V_r_dots, dVdxs, gs, u_ls)]) for V_r_dots, dVdxs, gs, u_ls in zip(V_r_dot_lst_sqs, dVdx_lst_sqs, g_lst_sqs, u_l_lst_sqs)]
#
# b_lst_sqs = [array([V_r_dot - dot(qp_controller.LgV(x, t), u_l) for V_r_dot, x, u_l, t in zip(V_r_dots, xs, u_ls, ts)]) for V_r_dots, xs, u_ls, ts in zip(V_r_dot_lst_sqs, x_lst_sqs, u_l_lst_sqs, t_lst_sqs)]
#
# # b_lst_sqs = [array([dot(a, u_c + u_l) + b for a, u_c, u_l, b in zip(a_true_lst_sq, u_c_lst_sq, u_l_lst_sq, b_true_lst_sq)]) for a_true_lst_sq, u_c_lst_sq, u_l_lst_sq, b_true_lst_sq in zip(a_true_lst_sqs, u_c_lst_sqs, u_l_lst_sqs, b_true_lst_sqs)]
#
# ests = [lstsq(A, b)[0] for A, b in zip(A_lst_sqs, b_lst_sqs)]
#
# a_true_compares = [a_trues[loss_upper_idx] / principal_scaling_episodes[loss_upper_idx] for loss_upper_idx in loss_upper_idxs]
# b_true_compares = [b_trues[loss_upper_idx] / principal_scaling_episodes[loss_upper_idx] for loss_upper_idx in loss_upper_idxs]
#
# for est, a_true_compare, b_true_compare, loss_upper_idx, x_lst_sq, A_lst_sq, b_lst_sq, b_lst_sq_wrong in zip(ests, a_true_compares, b_true_compares, loss_upper_idxs, x_lst_sqs, A_lst_sqs, b_lst_sqs, b_lst_sq_wrongs):
#     print('Least squares @', loss_upper_idx)
#     print('EST: ', est)
#     print('TRUE:', append(a_true_compare, b_true_compare))
#     print(x_lst_sq)
#     print(A_lst_sq)
#     print(b_lst_sq)
#     print(b_lst_sq_wrong)

x_animates = split(x_episodes, num_episodes)
u_c_animates = split(u_c_episodes, num_episodes)
u_l_animates = split(u_l_episodes, num_episodes)
ts = t_eval[half_L:-half_L-1:subsample_rate]

x_min, theta_min, x_dot_min, theta_dot_min = min(x_episodes, 0)
x_max, theta_max, x_dot_max, theta_dot_max = max(x_episodes, 0)
u_c_min = min(u_c_episodes[:, 0])
u_c_max = max(u_c_episodes[:, 0])
u_min = min((u_c_episodes + u_l_episodes)[:, 0])
u_max = max((u_c_episodes + u_l_episodes)[:, 0])
mins = [x_min, theta_min, u_c_min, x_dot_min, theta_dot_min, u_min]
maxs = [x_max, theta_max, u_c_max, x_dot_max, theta_dot_max, u_max]
t_0, t_final = ts[0], ts[-1]

f = figure()
axs = f.subplots(2, 3)

ax_ds = reshape(axs[0:2, 0:2], -1)
for ax_d, traj_d in zip(ax_ds, x_ds.T):
    ax_d.plot(t_ds, traj_d, '--')

axs = reshape(axs, -1)
titles = ['$x$', '$\\theta$', '$u_c$', '$\\dot{x}$', '$\\dot{\\theta}$', '$u_c + u_l$']

for ax, title, minimum, maximum in zip(axs, titles, mins, maxs):
    ax.set_xlim(t_0, t_final)
    ax.set_ylim(min([0.9 * minimum, 1.1 * minimum]), max([0.9 * maximum, 1.1 * maximum]))
    ax.set_title(title, fontsize=16)
    ax.grid()
lines = [ax.plot([], [], linewidth=2)[0] for ax in axs]

def update(frame):
    xs, thetas, x_dots, theta_dots = x_animates[frame].T
    u_cs = u_c_animates[frame][:, 0]
    u_ls = u_l_animates[frame][:, 0]
    us = u_cs + u_ls

    trajs = [xs, thetas, u_cs, x_dots, theta_dots, us]

    for line, traj in zip(lines, trajs):
        line.set_data(ts, traj)

    return lines

_ = FuncAnimation(f, update, frames=range(num_episodes), blit=True, interval=500, repeat=True, repeat_delay=2000)

show(f)
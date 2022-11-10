import os.path

import segyio as sgy
import numpy as np
import math
import re


def check_input(input_str):
    if input_str == '':
        return False
    try:
        float(input_str)
    except ValueError:
        return False
    return True


def read_par(filename):
    X0 = Y0 = step = 0
    with open(filename) as f:
        lines = f.readlines()
    for l in lines:
        if 'zeroX_model' in l:
            X0 = int(re.findall(r'\d+', l)[0])
        if 'zeroY_model' in l:
            Y0 = int(re.findall(r'\d+', l)[0])
        if 'stepX_model' in l:
            step = int(re.findall(r'\d+', l)[0])
    return X0, Y0, step


def read_segy(filename, xbyte, ybyte, inlbyte, xlnbyte, window):
    read_ok = True
    byte_x = int(xbyte[:3])
    byte_y = int(ybyte[:3])
    byte_inline = int(inlbyte[:3])
    byte_xline = int(xlnbyte[:3])
    try:
        with sgy.open(filename, ignore_geometry=True) as segyfile:
            segyfile.mmap()
            window['-PROG-'].update(current_count=0, max=segyfile.tracecount // 100)
            inlines = []
            xlines = []
            x = []
            y = []
            for i in range(segyfile.tracecount):
                header = segyfile.header[i]

                inlines.append(header[byte_inline])
                xlines.append(header[byte_xline])
                x.append(header[byte_x])
                y.append(header[byte_y])
                if i % 100 == 0:
                    window['-PROG-'].update(i // 100 + 1)

    except (UnboundLocalError, RuntimeError):
        read_ok = False
        return read_ok, None, None, None, None

    return read_ok, inlines, xlines, x, y


def calc_alpha(c1, c2):
    return np.degrees(np.arctan(c1 / c2))


def get_regression(inlines, xlines, x, y):
    X = np.vstack([inlines, xlines]).T
    X = np.c_[X, np.ones(X.shape[0])]
    linreg_x = np.linalg.lstsq(X, np.array(x), rcond=None)[0]
    linreg_y = np.linalg.lstsq(X, np.array(y), rcond=None)[0]
    np.save('linreg_x.npy', linreg_x)
    np.save('linreg_y.npy', linreg_y)

    X = np.vstack([x, y]).T
    X = np.c_[X, np.ones(X.shape[0])]
    linreg_inl = np.linalg.lstsq(X, np.array(inlines), rcond=None)[0]
    linreg_xln = np.linalg.lstsq(X, np.array(xlines), rcond=None)[0]
    np.save('linreg_inl.npy', linreg_inl)
    np.save('linreg_xln.npy', linreg_xln)

    step = np.sqrt(linreg_x[0] ** 2 + linreg_x[1] ** 2)
    inline_along_y = math.copysign(1.0, linreg_x[0] * linreg_y[1]) == -1

    # вариант через тангенс даёт верный результат в 1 и 4 четвертях. Вариант через косинус - в 1 и 2
    # учитывая, что 1 и 4 наиболее частый вариант, то оставляю тангенс
    if inline_along_y:

        alpha = np.degrees(np.arctan(linreg_x[0] / linreg_x[1]))
    else:

        alpha = np.degrees(np.arctan(linreg_x[1] / linreg_x[0]))

    return {
        'x_coefs': linreg_x.tolist(),
        'y_coefs': linreg_y.tolist(),
        'inline_coefs': linreg_inl.tolist(),
        'xline_coefs': linreg_xln.tolist()
    }


def get_linear_from_ab(a, b, coefs1, coefs2):
    c = coefs1[0] * a + coefs1[1] * b + coefs1[2]
    d = coefs2[0] * a + coefs2[1] * b + coefs2[2]
    return c, d


def rotate_coords(x0, y0, alpha):
    x = x0 * np.cos(np.radians(alpha)) - y0 * np.sin(np.radians(alpha))
    y = x0 * np.sin(np.radians(alpha)) + y0 * np.cos(np.radians(alpha))
    return x, y


def load_reg(values):
    if os.path.isfile('linreg_x.npy'):
        linreg_x = np.load('linreg_x.npy')
    else:
        linreg_x = [float(values['x_coef1']), float(values['x_coef2']), float(values['x_coef3'])]
    if os.path.isfile('linreg_y.npy'):
        linreg_y = np.load('linreg_y.npy')
    else:
        linreg_y = [float(values['y_coef1']), float(values['y_coef2']), float(values['y_coef3'])]
    if os.path.isfile('linreg_inl.npy'):
        linreg_inl = np.load('linreg_inl.npy')
    else:
        linreg_inl = [float(values['inl_coef1']), float(values['inl_coef2']), float(values['inl_coef3'])]
    if os.path.isfile('linreg_xln.npy'):
        linreg_xln = np.load('linreg_xln.npy')
    else:
        linreg_xln = [float(values['xln_coef1']), float(values['xln_coef2']), float(values['xln_coef3'])]
    return linreg_x, linreg_y, linreg_inl, linreg_xln


def calc_coords(filename, linreg_x, linreg_y, linreg_inl, linreg_xln, values, window):
    alpha = - np.degrees(np.arctan(linreg_x[0] / linreg_x[1]))
    x0_rot, y0_rot = rotate_coords(float(values['proc_x0']), float(values['proc_y0']), alpha)
    # x0_rot = float(values['proc_x0']) * np.cos(np.radians(alpha)) - float(values['proc_y0']) * np.sin(np.radians(alpha))
    # y0_rot = float(values['proc_x0']) * np.sin(np.radians(alpha)) + float(values['proc_y0']) * np.cos(np.radians(alpha))
    try:
        with sgy.open(filename, 'r+', ignore_geometry=True) as f:
            # f.mmap()
            cdp_x_array = []
            cdp_y_array = []
            inline_array = []
            xline_array = []
            for i in range(f.tracecount):
                x = (f.header[i][5] - f.header[0][5]) * float(values['proc_step']) + x0_rot
                y = (f.header[i][1] - f.header[0][1]) * float(values['proc_step']) + y0_rot
                x_rot = x * np.cos(np.radians(alpha)) - y * np.sin(np.radians(alpha))
                y_rot = x * np.sin(np.radians(alpha)) + y * np.cos(np.radians(alpha))
                f.header[i][181] = int(np.round(x_rot))
                f.header[i][185] = int(np.round(y_rot))
                cdp_x_array.append(f.header[i][181])
                cdp_y_array.append(f.header[i][185])
                # inl, xln = get_linear_from_ab(x_rot, y_rot, linreg_inl, linreg_xln)
                f.header[i][189] = int(np.round(linreg_inl[0] * x_rot + linreg_inl[1] * y_rot + linreg_inl[2]))
                f.header[i][193] = int(np.round(linreg_xln[0] * x_rot + linreg_xln[1] * y_rot + linreg_xln[2]))
                inline_array.append(f.header[i][189])
                xline_array.append(f.header[i][193])
                f.header[i][17] = f.header[i][189]
                f.header[i][25] = f.header[i][193]

    except (UnboundLocalError, RuntimeError, OSError):
        return False, None, None, None, None

    return True, cdp_x_array, cdp_y_array, inline_array, xline_array


# скопировать заголовки из другого файла
def copy_headers(source, dest, cdp_x, cdp_y, inline, xline):
    try:
        with sgy.open(source, ignore_geometry=True) as f1:
            with sgy.open(dest,  'r+', ignore_geometry=True) as f2:
                # f2.header = f1.header
                for i in range(f1.tracecount):
                    f2.header[i][181] = cdp_x[i]
                    f2.header[i][185] = cdp_y[i]
                    f2.header[i][189] = inline[i]
                    f2.header[i][193] = xline[i]
                    f2.header[i][17] = cdp_x[i]
                    f2.header[i][25] = cdp_y[i]
    except (UnboundLocalError, RuntimeError, OSError):
        return False
    return True
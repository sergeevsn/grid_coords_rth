import PySimpleGUI as sg
import time
import os

from services import *


def read_params_window():
    layout = [[sg.Input(key='-PAR FILE-', enable_events=True, size=(40, 20)),
               sg.FileBrowse('Выбрать файл параметров', key='-CHOOSE-', change_submits=True,
                             file_types=(('PAR файлы', '*.par'), ('Все файлы', '*.*')),
                             target='-PAR FILE-')]]
    window = sg.Window('GridCoords: Выбор файла', layout)
    while True:
        event, values = window.read()
        # See if user wants to quit or window was closed

        if event == sg.WINDOW_CLOSED or event == '-QUIT-':
            break
        if event == '-PAR FILE-':

            x0 = y0 = step = 0
            if os.path.isfile(values['-PAR FILE-']):
                x0, y0, step = read_par(values['-PAR FILE-'])
            window.close()
            return x0, y0, step


def read_segy_window():
    layout = [[sg.Input(key='-SEGY FILE-', enable_events=True, size=(40, 20)),
               sg.FileBrowse('Выбрать SEG-Y файл', key='-CHOOSE-', change_submits=True,
                             file_types=(('SEG-Y файлы', '*.sgy'), ('Все файлы', '*.*')),
                             target='-SEGY FILE-')],
              [sg.Push()],
              [sg.Push()],
              [sg.Text("X-координата", size=(10, 1)), sg.Combo(['181 (CDP X)', '73 (Source X)', '81 (Receiver X)'],
                                                               default_value='181 (CDP X)', size=(13, 1),
                                                               key='x_byte')],
              [sg.Text("Y-координата", size=(10, 1)), sg.Combo(['185 (CDP Y)', '77 (Source Y)', '85 (Receiver Y)'],
                                                               default_value='185 (CDP Y)', size=(13, 1),
                                                               key='y_byte')],
              [sg.Text("Инлайны", size=(10, 1)), sg.Combo(['189 (Стандарт)', '17 (Kingdom)'],
                                                          default_value='189 (Стандарт)', size=(13, 1),
                                                          key='inline_byte')],
              [sg.Text("Кросслайны", size=(10, 1)), sg.Combo(['193 (Стандарт)', '25 (Kingdom)'],
                                                             default_value='193 (Стандарт)', size=(13, 1),
                                                             key='xline_byte')],
              [sg.ProgressBar(100, orientation='h', visible=False, size=(22, 20), key='-PROG-')]
              ]
    window = sg.Window('GridInfo: Выбор файла', layout)
    while True:
        event, values = window.read()
        # See if user wants to quit or window was closed

        if event == sg.WINDOW_CLOSED or event == '-QUIT-':
            break
        if event == '-SEGY FILE-':

            if os.path.isfile(values['-SEGY FILE-']):

                window['-CHOOSE-'].update(disabled=True)

                window['-PROG-'].update(visible=True)

                regr = None
                read_ok, inlines, xlines, x, y = read_segy(values['-SEGY FILE-'], values['x_byte'], values['y_byte'],
                                                           values['inline_byte'], values['xline_byte'], window)
                if not read_ok:
                    sg.PopupError('Wrong file')
                    break

                regr = get_regression(inlines, xlines, x, y)


                window.close()
                return regr


def clear_files():
    if os.path.isfile('linreg_x.npy'):
        os.remove('linreg_x.npy')
    if os.path.isfile('linreg_y.npy'):
        os.remove('linreg_y.npy')
    if os.path.isfile('linreg_inl.npy'):
        os.remove('linreg_inl.npy')
    if os.path.isfile('linreg_xln.npy'):
        os.remove('linreg_xln.npy')


def main():
    state = {'status': 'wait', 'file_list': [], 'file_index': 0, 'start_time': 0}
    fr1 = sg.Frame('Выбор папки', [[sg.In(size=(42, 1), enable_events=True, key='-FOLDER-')],
                                   [sg.FolderBrowse('Выбрать', key='folder', target='-FOLDER-')],



                                   ], size=(280, 160))
    fr2 = sg.Frame('Линейные коэффициенты грида', [[sg.Text('INL =', size=(4, 1)),
                                                    sg.In(size=(5, 1), enable_events=True, key='inl_coef1'),
                                                    sg.Text('*X + ', size=(4, 1)),
                                                    sg.In(size=(5, 1), enable_events=True, key='inl_coef2'),
                                                    sg.Text('*Y + ', size=(4, 1)),
                                                    sg.In(size=(8, 1), enable_events=True, key='inl_coef3')
                                                    ],
                                                   [sg.Text('XLN =', size=(4, 1)),
                                                    sg.In(size=(5, 1), enable_events=True, key='xln_coef1'),
                                                    sg.Text('*X + ', size=(4, 1)),
                                                    sg.In(size=(5, 1), enable_events=True, key='xln_coef2'),
                                                    sg.Text('*Y + ', size=(4, 1)),
                                                    sg.In(size=(8, 1), enable_events=True, key='xln_coef3')
                                                    ],
                                                   [sg.Text('X =', size=(4, 1)),
                                                    sg.In(size=(5, 1), enable_events=True, key='x_coef1'),
                                                    sg.Text('*INL+ ', size=(4, 1)),
                                                    sg.In(size=(5, 1), enable_events=True, key='x_coef2'),
                                                    sg.Text('*XLN+ ', size=(4, 1)),
                                                    sg.In(size=(8, 1), enable_events=True, key='x_coef3')
                                                    ],
                                                   [sg.Text('Y =', size=(4, 1)),
                                                    sg.In(size=(5, 1), enable_events=True, key='y_coef1'),
                                                    sg.Text('*INL+ ', size=(4, 1)),
                                                    sg.In(size=(5, 1), enable_events=True, key='y_coef2'),
                                                    sg.Text('*XLN+ ', size=(4, 1)),
                                                    sg.In(size=(8, 1), enable_events=True, key='y_coef3')
                                                    ],
                                                   [sg.Button('Взять из SEG-Y', key='segy')]], size=(320, 160))

    fr3 = sg.Frame('Параметры обработки',
                   [[sg.Text('X0', size=(6, 1)), sg.In(size=(11, 1), enable_events=True, key='proc_x0')],
                    [sg.Text('Y0', size=(6, 1)), sg.In(size=(11, 1), enable_events=True, key='proc_y0')],
                    [sg.Text('Шаг', size=(6, 1)), sg.In(size=(11, 1), enable_events=True, key='proc_step')],
                    [sg.FileBrowse('Выбрать файл параметров', key='par', change_submits=True,
                                   file_types=(('PAR файлы', '*.par'), ('Все файлы', '*.*')))]
                    ], size=(180, 160))

    layout = [[fr1, fr2, fr3],
              [sg.Button('Запуск', key='-RUN-', button_color='green'),
               sg.Button('Отмена', key='-STOP-', button_color='red', visible=False)],
              [sg.ProgressBar(180, orientation='h', visible=True, size=(73, 20), key='-PROG1-')],
              [sg.Text(key='now_processing')]
              ]


    # Create the window
    window = sg.Window('GridCoords', layout)

    # Display and interact with the Window using an Event Loop
    while True:
        event, values = window.read()

        if event == 'segy':
            regr = read_segy_window()
            if regr:
                window['x_coef1'].update(f"{regr['x_coefs'][0]:.3f}")
                window['x_coef2'].update(f"{regr['x_coefs'][1]:.3f}")
                window['x_coef3'].update(f"{regr['x_coefs'][2]:.2f}")
                window['y_coef1'].update(f"{regr['y_coefs'][0]:.3f}")
                window['y_coef2'].update(f"{regr['y_coefs'][1]:.3f}")
                window['y_coef3'].update(f"{regr['y_coefs'][2]:.2f}")
                window['inl_coef1'].update(f"{regr['inline_coefs'][0]:.3f}")
                window['inl_coef2'].update(f"{regr['inline_coefs'][1]:.3f}")
                window['inl_coef3'].update(f"{regr['inline_coefs'][2]:.2f}")
                window['xln_coef1'].update(f"{regr['xline_coefs'][0]:.3f}")
                window['xln_coef2'].update(f"{regr['xline_coefs'][1]:.3f}")
                window['xln_coef3'].update(f"{regr['xline_coefs'][2]:.2f}")

        if event == 'par':
            x0 = y0 = step = 0
            if os.path.isfile(values['par']):
                x0, y0, step = read_par(values['par'])
                window['proc_x0'].update(f"{x0:.2f}")
                window['proc_y0'].update(f"{y0:.2f}")
                window['proc_step'].update(f"{step:.2f}")

        if event == '-RUN-':
            if state['status'] == 'wait':

                if (check_input(values['x_coef1']) and check_input(values['x_coef2']) and check_input(values['x_coef3'])
                        and check_input(values['y_coef1']) and check_input(values['y_coef2'])
                        and check_input(values['y_coef3']) and check_input(values['inl_coef1'])
                        and check_input(values['inl_coef2']) and check_input(values['inl_coef3'])
                        and check_input(values['xln_coef1']) and check_input(values['xln_coef2']) and check_input(
                            values['xln_coef3'])
                        and check_input(values['proc_x0']) and check_input(values['proc_y0'])
                        and check_input(values['proc_step']) and os.path.isdir(values['-FOLDER-'])):
                    num_files = sum([len(fnames) for r, d, fnames in os.walk(values['-FOLDER-'])])
                    reg = load_reg(values)
                    window['-STOP-'].update(visible=True)
                    window['-RUN-'].update(visible=False)
                    window['-PROG1-'].update(visible=True, current_count=0, max=num_files)

                    for root, dirs, files in os.walk(values['-FOLDER-']):
                        for filename in files:
                            full_filename = os.path.join(root, filename)
                            if full_filename[-4:] == '.sgy':
                                state['file_list'].append(full_filename)
                    state['status'] = 'run'
                    state['file_index'] = 0
                    state['start_time'] = time.time()
                    window.write_event_value('-NEXT-', '')

                else:
                    break
        if event == '-NEXT-':
            if state['status'] == 'run':
                if state['file_index'] < len(state['file_list']):
                    index = state['file_index']
                    fname = state['file_list'][index]

                    window['now_processing'].update(fname)
                    if state['file_index'] == 0:
                        status, cdp_x, cdp_y, inline, xline = calc_coords(fname, *reg, values, window)
                    else:
                        copy_headers(state['file_list'][0], fname,  cdp_x, cdp_y, inline, xline)
                    window['-PROG1-'].update(state['file_index'] + 1)
                    state['file_index'] += 1
                    window.write_event_value('-NEXT-', '')
                else:
                    window.write_event_value('-STOP-', '')
        if event == '-STOP-':
            window['-STOP-'].update(visible=False)
            window['-RUN-'].update(visible=True)
            window['-PROG1-'].update(0)

            duration = (time.time() - state['start_time'])
            sg.popup(f"Обработано файлов: ({state['file_index']}) за {duration:.2f} сек.")
            state['file_index'] = []
            state['file_index'] = 0
            clear_files()
            state['start_time'] = 0
            state['status'] = 'wait'

        # See if user wants to quit or window was closed
        if event == sg.WINDOW_CLOSED:
            clear_files()
            break


if __name__ == "__main__":
    main()

import sys
import os
import subprocess
from PyQt5 import QtWidgets, QtCore, QtGui
from PIL import Image
import threading


DEFAULT_BLENDER = r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe"
BLENDER_SCRIPT_NAME = "blender_render_helper.py"

class SpriteGUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('DOOMlike Sprite Generator')
        self.setMinimumSize(750, 950)
        self.resize(800, 1080)
        self.setStyleSheet('''
            QWidget {
                background-color: #1a1a1a;
                color: #e0e0e0;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 13px;
            }
            QLabel {
                color: #e0e0e0;
                font-weight: 500;
            }
            QLabel#sectionLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 0px 4px 0px;
            }
            QLabel#fileLabel {
                background-color: #252525;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 10px;
                color: #888;
                min-height: 16px;
            }
            QLabel#fileLabel[loaded="true"] {
                color: #66ff66;
                border-color: #66ff66;
            }
            QPushButton {
                background-color: #2a2a2a;
                border: 2px solid #444;
                border-radius: 6px;
                padding: 8px 16px;
                color: #e0e0e0;
                font-weight: 600;
                min-height: 16px;
            }
            QPushButton:hover {
                background-color: #353535;
                border-color: #666;
            }
            QPushButton:pressed {
                background-color: #202020;
            }
            QPushButton#generateBtn {
                background-color: #404040;
                border-color: #ffffff;
                color: white;
                font-size: 14px;
                min-height: 24px;
                padding: 10px;
            }
            QPushButton#generateBtn:hover {
                background-color: #555555;
            }
            QPushButton#generateBtn:pressed {
                background-color: #2a2a2a;
            }
            QLineEdit {
                background-color: #252525;
                border: 2px solid #3a3a3a;
                border-radius: 4px;
                padding: 8px;
                color: #e0e0e0;
                min-height: 16px;
            }
            QLineEdit:focus {
                border-color: #ffffff;
            }
            QTextEdit {
                background-color: #0a0a0a;
                border: 2px solid #3a3a3a;
                border-radius: 4px;
                color: #888;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 11px;
            }
            QGroupBox {
                border: 2px solid #3a3a3a;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
                font-weight: bold;
            }
            QGroupBox::title {
                color: #ffffff;
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        ''')
        
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 15, 20, 15)

        blender_group = QtWidgets.QGroupBox('Blender Configuration')
        blender_layout = QtWidgets.QVBoxLayout()
        
        row = QtWidgets.QHBoxLayout()
        self.blender_path = QtWidgets.QLineEdit(DEFAULT_BLENDER)
        row.addWidget(self.blender_path, 1)
        self.btn_browse_blender = QtWidgets.QPushButton('Browse')
        row.addWidget(self.btn_browse_blender)
        blender_layout.addLayout(row)
        blender_group.setLayout(blender_layout)
        main_layout.addWidget(blender_group)

        # File inputs n stuff
        files_group = QtWidgets.QGroupBox('Input Files')
        files_layout = QtWidgets.QVBoxLayout()
        
        self.model_label = QtWidgets.QLabel('No model selected')
        self.model_label.setObjectName('fileLabel')
        files_layout.addWidget(self.model_label)
        
        self.btn_model = QtWidgets.QPushButton('Load 3D Model')
        files_layout.addWidget(self.btn_model)
        
        files_layout.addSpacing(10)
        
        self.texture_label = QtWidgets.QLabel('No texture selected (optional)')
        self.texture_label.setObjectName('fileLabel')
        files_layout.addWidget(self.texture_label)
        
        self.btn_texture = QtWidgets.QPushButton('Load Texture')
        files_layout.addWidget(self.btn_texture)
        
        files_group.setLayout(files_layout)
        main_layout.addWidget(files_group)

        settings_group = QtWidgets.QGroupBox('Render Settings')
        form = QtWidgets.QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(QtCore.Qt.AlignRight)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.ExpandingFieldsGrow)
        
        self.base_name = QtWidgets.QLineEdit('monster')
        self.img_size = QtWidgets.QLineEdit('512')
        self.pixel_size = QtWidgets.QLineEdit('64')
        
        form.addRow('Sprite name:', self.base_name)
        form.addRow('Render size:', self.img_size)
        form.addRow('Final pixel size:', self.pixel_size)
        
        rotation_label = QtWidgets.QLabel('Model Rotation Correction')
        rotation_label.setObjectName('sectionLabel')
        form.addRow('', rotation_label)
        
        self.rotX = QtWidgets.QLineEdit('0')
        self.rotY = QtWidgets.QLineEdit('0')
        self.rotZ = QtWidgets.QLineEdit('0')
        
        form.addRow('Rotate X (pitch):', self.rotX)
        form.addRow('Rotate Y (roll):', self.rotY)
        form.addRow('Rotate Z (yaw):', self.rotZ)

        camera_label = QtWidgets.QLabel('Camera Settings')
        camera_label.setObjectName('sectionLabel')
        form.addRow('', camera_label)
        
        self.camAngle = QtWidgets.QLineEdit('90')
        form.addRow('Camera angle:', self.camAngle)
        
        settings_group.setLayout(form)
        main_layout.addWidget(settings_group)

        self.btn_generate = QtWidgets.QPushButton('GENERATE SPRITES')
        self.btn_generate.setObjectName('generateBtn')
        main_layout.addWidget(self.btn_generate)
        
        # Progress bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat('Rendering sprites...')
        self.progress_bar.setStyleSheet('''
            QProgressBar {
                border: 2px solid #3a3a3a;
                border-radius: 6px;
                text-align: center;
                background-color: #1a1a1a;
                color: #ffffff;
                font-weight: bold;
                min-height: 24px;
            }
            QProgressBar::chunk {
                background-color: #555555;
            }
        ''')
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

        # Logs
        log_label = QtWidgets.QLabel('Console Output')
        log_label.setObjectName('sectionLabel')
        main_layout.addWidget(log_label)
        
        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(120)
        main_layout.addWidget(self.log)

        self.setLayout(main_layout)
        self.model_path = None
        self.texture_path = None

        self.btn_model.clicked.connect(self.load_model)
        self.btn_texture.clicked.connect(self.load_texture)
        self.btn_browse_blender.clicked.connect(self.browse_blender)
        self.btn_generate.clicked.connect(self.generate)

    def append_log(self, *parts):
        if len(parts) == 1:
            self.log.append(parts[0])
        else:
            self.log.append(' '.join(str(p) for p in parts))

    def browse_blender(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Locate Blender executable', '', 'blender.exe (blender.exe)')
        if p:
            self.blender_path.setText(p)

    def load_model(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Select 3D Model', '', 'Models (*.obj *.fbx *.gltf *.glb)')
        if p:
            self.model_path = p
            self.model_label.setText(f'Model: {os.path.basename(p)}')
            self.model_label.setProperty('loaded', 'true')
            self.model_label.style().unpolish(self.model_label)
            self.model_label.style().polish(self.model_label)

    def load_texture(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Select Texture', '', 'Images (*.png *.jpg *.jpeg)')
        if p:
            self.texture_path = p
            self.texture_label.setText(f'Texture: {os.path.basename(p)}')
            self.texture_label.setProperty('loaded', 'true')
            self.texture_label.style().unpolish(self.texture_label)
            self.texture_label.style().polish(self.texture_label)

    def generate(self):
        blender = self.blender_path.text().strip()
        if not blender or not os.path.isfile(blender):
            QtWidgets.QMessageBox.warning(self, 'Error', 'Blender executable not found.')
            return
        if not self.model_path:
            QtWidgets.QMessageBox.warning(self, 'Error', 'No model selected.')
            return
        base = self.base_name.text().strip()
        if not base:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Enter a base name.')
            return
        try:
            img_size = int(self.img_size.text().strip())
            rotX = float(self.rotX.text().strip())
            rotY = float(self.rotY.text().strip())
            rotZ = float(self.rotZ.text().strip())
            camAngle = float(self.camAngle.text().strip())
            pixel_size = int(self.pixel_size.text().strip())
        except Exception:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Rotation, camera angle, and sizes must be numeric.')
            return

        # Disable button and show progress bar
        self.btn_generate.setEnabled(False)
        self.progress_bar.show()
        self.log.clear()
        
        # Run generation in a separate thread
        thread = threading.Thread(target=self._run_generation, args=(blender, base, img_size, rotX, rotY, rotZ, camAngle, pixel_size))
        thread.daemon = True
        thread.start()

    def _run_generation(self, blender, base, img_size, rotX, rotY, rotZ, camAngle, pixel_size):
        try:
            out_dir = os.path.join(os.getcwd(), 'output_sprites')
            os.makedirs(out_dir, exist_ok=True)

            if getattr(sys, 'frozen', False):
                # We are running in a bundle
                base_path = sys._MEIPASS
            else:
                # We are running in a normal Python environment
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            script_path = os.path.join(base_path, BLENDER_SCRIPT_NAME)
            if not os.path.exists(script_path):
                 raise FileNotFoundError(f"Helper script not found at {script_path}")

            tex_arg = self.texture_path if self.texture_path else ''
            args = [blender, '-b', '--python', script_path, '--', self.model_path, tex_arg, out_dir, base, str(img_size), str(rotX), str(rotY), str(rotZ), str(camAngle)]
            
            QtCore.QMetaObject.invokeMethod(self, "append_log", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, 'Starting Blender render...'))
            QtCore.QMetaObject.invokeMethod(self, "append_log", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, 'Command: ' + ' '.join(args)))

            proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=True)
            QtCore.QMetaObject.invokeMethod(self, "append_log", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, proc.stdout))

            # Post-process: First pixelate, THEN crop
            QtCore.QMetaObject.invokeMethod(self, "append_log", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, f'Downscaling to {pixel_size}x{pixel_size}...'))
            
            # First pass: pixelate all images
            sprite_files = [f for f in os.listdir(out_dir) if f.endswith('.png') and f.startswith(base)]
            for file in sprite_files:
                img_path = os.path.join(out_dir, file)
                img = Image.open(img_path).convert('RGBA')
                img = img.resize((pixel_size, pixel_size), Image.NEAREST)
                img.save(img_path, optimize=False)
            
            QtCore.QMetaObject.invokeMethod(self, "append_log", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, 'Finding optimal crop bounds...'))
            
            # Second pass: find the maximum bounding box across all pixelated sprites
            max_bbox = None
            for file in sprite_files:
                img_path = os.path.join(out_dir, file)
                img = Image.open(img_path).convert('RGBA')
                
                # Get bounding box of non-transparent pixels
                bbox = img.getbbox()
                if bbox:
                    width = bbox[2] - bbox[0]
                    height = bbox[3] - bbox[1]
                    if max_bbox is None:
                        max_bbox = (width, height)
                    else:
                        max_bbox = (max(max_bbox[0], width), max(max_bbox[1], height))
            
            if max_bbox is None:
                QtCore.QMetaObject.invokeMethod(self, "append_log", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, 'Warning: No visible pixels found in sprites'))
            else:
                QtCore.QMetaObject.invokeMethod(self, "append_log", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, f'Cropping all sprites to {max_bbox[0]}x{max_bbox[1]} pixels...'))
                
                # Third pass: crop all sprites to the same uniform size
                for file in sprite_files:
                    img_path = os.path.join(out_dir, file)
                    img = Image.open(img_path).convert('RGBA')
                    
                    # Get bounding box and crop
                    bbox = img.getbbox()
                    if bbox:
                        cropped = img.crop(bbox)
                        
                        # Create a new image with the maximum dimensions
                        final_img = Image.new('RGBA', max_bbox, (0, 0, 0, 0))
                        
                        # Center the cropped sprite in the final image
                        x_offset = (max_bbox[0] - cropped.width) // 2
                        y_offset = (max_bbox[1] - cropped.height) // 2
                        final_img.paste(cropped, (x_offset, y_offset))
                        
                        final_img.save(img_path, optimize=False)
                        QtCore.QMetaObject.invokeMethod(self, "append_log", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, f'  Processed: {file}'))

            QtCore.QMetaObject.invokeMethod(self, "append_log", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, f'Complete! Sprites saved to: {out_dir}'))
            QtCore.QMetaObject.invokeMethod(self, "show_success", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, out_dir))
        except subprocess.CalledProcessError as e:
            QtCore.QMetaObject.invokeMethod(self, "append_log", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, 'ERROR: Blender returned non-zero exit code'))
            QtCore.QMetaObject.invokeMethod(self, "append_log", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, e.stdout))
            QtCore.QMetaObject.invokeMethod(self, "show_error", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, 'Blender failed. See console log for details.'))
        except Exception as e:
            QtCore.QMetaObject.invokeMethod(self, "append_log", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, f'ERROR: {str(e)}'))
            QtCore.QMetaObject.invokeMethod(self, "show_error", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, f'An error occurred: {str(e)}'))
        finally:
            pass
            # Re-enable button and hide progress bar
            QtCore.QMetaObject.invokeMethod(self, "finish_generation", QtCore.Qt.QueuedConnection)

    @QtCore.pyqtSlot()
    def finish_generation(self):
        self.btn_generate.setEnabled(True)
        self.progress_bar.hide()

    @QtCore.pyqtSlot(str)
    def show_success(self, out_dir):
        QtWidgets.QMessageBox.information(self, 'Success', f'All sprites generated!\n\nLocation: {out_dir}')

    @QtCore.pyqtSlot(str)
    def show_error(self, message):
        QtWidgets.QMessageBox.critical(self, 'Error', message)

    @QtCore.pyqtSlot(str)
    def append_log(self, text):
        self.log.append(text)


def main():
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    
    app = QtWidgets.QApplication(sys.argv)
    gui = SpriteGUI()
    gui.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

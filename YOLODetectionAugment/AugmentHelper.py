import cv2
import os
import shutil
import xml.etree.ElementTree as ET
from tqdm import tqdm
import numpy as np
import glob

from .spltdata import split_img
from .ToXml import yolov5txt2xml
from .enlarge import *


def delete_folder(path):
    try:
        shutil.rmtree(path)
    except OSError as e:
        pass


def doAugument(source_img_path, source_xml_path, save_img_path, save_xml_path, need_aug_num=3):
    dataAug = DataAugmentForObjectDetection()
    toolhelper = ToolHelper()

    if not os.path.exists(save_img_path):
        os.mkdir(save_img_path)
    if not os.path.exists(save_xml_path):
        os.mkdir(save_xml_path)

    file_list = []
    for parent, _, files in os.walk(source_img_path):
        files.sort()
        for file in files:
            file_list.append((parent, file))

    for parent, file in tqdm(file_list, desc="数据增强中"):
        cnt = 0
        pic_path = os.path.join(parent, file)
        xml_path = os.path.join(source_xml_path, file[:-4] + '.xml')
        try:
            values = toolhelper.parse_xml(xml_path)
        except:
            print("error")
            continue
        coords = [v[:4] for v in values]
        labels = [v[-1] for v in values]

        dot_index = file.rfind('.')
        _file_prefix = file[:dot_index]
        _file_suffix = file[dot_index:]

        img = cv2.imread(pic_path)

        while cnt < need_aug_num:
            auged_img, auged_bboxes = dataAug.dataAugment(img, coords)
            auged_bboxes_int = np.array(auged_bboxes).astype(np.int32)
            height, width, channel = auged_img.shape
            img_name = '{}_MM{}{}'.format(_file_prefix, cnt + 1, _file_suffix)
            toolhelper.save_img(img_name, save_img_path, auged_img)
            toolhelper.save_xml('{}_MM{}.xml'.format(_file_prefix, cnt + 1),
                                save_xml_path, (save_img_path, img_name), height, width, channel,
                                (labels, auged_bboxes_int))
            cnt += 1


def convert(size, box):
    dw = 1. / size[0]
    dh = 1. / size[1]
    x = (box[0] + box[1]) / 2.0
    y = (box[2] + box[3]) / 2.0
    w = box[1] - box[0]
    h = box[3] - box[2]
    x = x * dw
    w = w * dw
    y = y * dh
    h = h * dh
    return (x, y, w, h)


def convert_annotation(SAVE, data_dir, imageset1, imageset2, image_id):
    in_file = open(data_dir + '/%s/%s.xml' % (imageset1, image_id), encoding='UTF-8')
    out_file = open(SAVE + '/%s.txt' % (image_id), 'w', encoding='UTF-8')

    tree = ET.parse(in_file)
    root = tree.getroot()
    size = root.find('size')
    w = int(size.find('width').text)
    h = int(size.find('height').text)
    for obj in root.iter('object'):
        difficult = obj.find('difficult').text
        cls = obj.find('name').text
        if cls not in classes or int(difficult) == 1:
            continue
        cls_id = classes.index(cls)
        xmlbox = obj.find('bndbox')
        b = (float(xmlbox.find('xmin').text), float(xmlbox.find('xmax').text), float(xmlbox.find('ymin').text),
             float(xmlbox.find('ymax').text))
        bb = convert((w, h), b)
        out_file.write(str(cls_id) + " " + " ".join([str('%.6f' % a) for a in bb]) + '\n')


def convertYOLO(SAVE, image_set, imageset2):
    image_ids = []
    for x in glob.glob(data_dir + '/%s' % image_set + '/*.xml'):
        image_ids.append(os.path.basename(x)[:-4])
    total_count = len(image_ids)
    print(f'\n{image_set} 数量: {total_count}')
    for image_id in tqdm(image_ids, desc=f"{image_set} 转换中"):
        convert_annotation(SAVE, data_dir, image_set, imageset2, image_id)
    print("Done!!!")

def change_extension_to_png(path_img):
    if not os.path.exists(path_img):
        return
    for filename in os.listdir(path_img):
        file_path = os.path.join(path_img, filename)
        if os.path.isfile(file_path):
            file_name, _ = os.path.splitext(filename)
            new_file_name = f"{file_name}.png"
            new_file_path = os.path.join(path_img, new_file_name)
            try:
                os.rename(file_path, new_file_path)
            except Exception as e:
                pass

def process_yolo_dataset(img_path, label_path, split_list, dics, need_aug_num_train=3, need_aug_num_val=2):
    global classes, data_dir
    change_extension_to_png(img_path)
    classes = list(dics.keys())
    data_dir = os.getcwd()

    delete_folder("bboxupload/img/.ipynb_checkpoints")
    delete_folder("bboxupload/label/.ipynb_checkpoints")
    delete_folder("DataSet2parts")

    split_img(img_path, label_path, split_list)

    train = r"DataSet2parts/images/train"
    val = r"DataSet2parts/images/val"
    trainLabel = r"DataSet2parts/labels/train"
    valLabel = r"DataSet2parts/labels/val"

    yolov5txt2xml(train, trainLabel, gt_labels=classes)
    yolov5txt2xml(val, valLabel, gt_labels=classes)

    trainLabel += "/out_dir_xml"
    valLabel += "/out_dir_xml"

    doAugument(train, trainLabel, 'trainAug', 'trainAugXML', need_aug_num=need_aug_num_train)
    doAugument(val, valLabel, 'testAug', 'testAugXML', need_aug_num=need_aug_num_val)

    convertYOLO("trainAug", "trainAugXML", "trainAug")
    convertYOLO("testAug", "testAugXML", "testAug")

    delete_folder("DataSet2parts")
    delete_folder("trainAugXML")
    delete_folder("testAugXML")


'''
if __name__ == "__main__":
    img_path = 'bboxupload/img'

    label_path = 'bboxupload/label'
    split_list = [0.9, 0.1]
    dics={"battery":0,"bottle":1,"brick":2,"can":3,'carrot':4,'glass':5,'medicine':6,'mooli':7,'package':8,'pebble':9,'potato':10}
    process_yolo_dataset(img_path, label_path, split_list, dics)
'''
# Copyright 2018 The TensorFlow Authors All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

"""Provides data from semantic regression datasets.

The SegmentationDataset class provides both images and annotations (semantic
segmentation and/or instance segmentation) for TensorFlow. Currently, we
support the following datasets:

1. PASCAL VOC 2012 (http://host.robots.ox.ac.uk/pascal/VOC/voc2012/).

PASCAL VOC 2012 semantic segmentation dataset annotates 20 foreground objects
(e.g., bike, person, and so on) and leaves all the other semantic classes as
one background class. The dataset contains 1464, 1449, and 1456 annotated
images for the training, validation and test respectively.

2. Cityscapes dataset (https://www.cityscapes-dataset.com)

The Cityscapes dataset contains 19 semantic labels (such as road, person, car,
and so on) for urban street scenes.

3. ADE20K dataset (http://groups.csail.mit.edu/vision/datasets/ADE20K)

The ADE20K dataset contains 150 semantic labels both urban street scenes and
indoor scenes.

References:
  M. Everingham, S. M. A. Eslami, L. V. Gool, C. K. I. Williams, J. Winn,
  and A. Zisserman, The pascal visual object classes challenge a retrospective.
  IJCV, 2014.

  M. Cordts, M. Omran, S. Ramos, T. Rehfeld, M. Enzweiler, R. Benenson,
  U. Franke, S. Roth, and B. Schiele, "The cityscapes dataset for semantic urban
  scene understanding," In Proc. of CVPR, 2016.

  B. Zhou, H. Zhao, X. Puig, S. Fidler, A. Barriuso, A. Torralba, "Scene Parsing
  through ADE20K dataset", In Proc. of CVPR, 2017.
"""
import collections
import os.path
import tensorflow as tf
import numpy as np

slim = tf.contrib.slim

dataset = slim.dataset

tfexample_decoder = slim.tfexample_decoder


_ITEMS_TO_DESCRIPTIONS = {
    'image': 'A color image of varying height and width.',
    'labels_class': ('A semantic regression label whose size matches image.'
                     'Its values range from 0 (background) to real values (pose and shape representations).'),
}

# Named tuple to describe the dataset properties.
DatasetDescriptor = collections.namedtuple(
    'DatasetDescriptor',
    ['splits_to_sizes',   # Splits of the dataset into training, val, and test.
     'num_classes',   # Number of semantic classes, including the background
                      # class (if exists). For example, there are 20
                      # foreground classes + 1 background class in the PASCAL
                      # VOC 2012 dataset. Thus, we set num_classes=21.
     # 'ignore_label',  # Ignore label value.
     'shape_dims',
     'shape_bins',
     # 'height',
     # 'width',
     'height_ori',
     'width_ori',
     'pose_range',
     'bin_nums',
     'output_names',
     'output_names_summary',
    ]
)

SHAPE_DIMS = 10
SHAPE_BINS = 32
POSE_BINS = 128

_APOLLOSCAPE_INFORMATION = DatasetDescriptor(
    splits_to_sizes={
        'train': 4611,
        'val': 480,
        'test': 1041
        # 'train': 731,
        # 'val': 107,
    },
    num_classes=7+2,
    shape_dims = SHAPE_DIMS,
    shape_bins = SHAPE_BINS,
    height_ori=678,
    width_ori=1692,
    # height = 272,
    # width = 680,
    # pose_range = [[-1., 1.],
    #     [-1., 1.],
    #     [-1., 1.],
    #     [-1., 1.],
    #     [-100., 100.],
    #     [0., 100],
    #     [0., 0.66]],
    # bin_nums = [32, 32, 32, 32, 64, 64, 64, SHAPE_DIMS, 79],
    # output_names = ['q1', 'q2', 'q3', 'q4', 'x', 'y', 'z', 'shape', 'shape_id_map'],
    pose_range = [[-1., 1.],
        [-1., 1.],
        [-1., 1.],
        [-1., 1.],
        # [-100., 100.], # x
        # [0., 50], # y
        [-0., 0.], # WHATEVRR: no cls for u
        [-0., 0.], # WHATEVER: no cls for v
        # [1.5, 350.]], # for depth
        [1.1, 350.], # for Dense depth
        [0., 0.]], # WHATEVER: no cls for Dense depth offset
    bin_nums = [POSE_BINS]*4 + [1, 1, POSE_BINS, 1] + [SHAPE_BINS]*SHAPE_DIMS, # uv flow
    # bin_nums = [POSE_BINS]*7 + [SHAPE_BINS]*SHAPE_DIMS, # xy
    output_names = ['q1', 'q2', 'q3', 'q4', 'x', 'y', 'z_log_dense', 'z_log_offset'] + ['shape_%d'%dim for dim in range(SHAPE_DIMS)],
    output_names_summary = ['q1', 'q2', 'q3', 'q4', 'x', 'y', 'z_object'] + ['shape_%d'%dim for dim in range(SHAPE_DIMS)],
)

_DATASETS_INFORMATION = {
    'apolloscape': _APOLLOSCAPE_INFORMATION,
}

# Default file pattern of TFRecord of TensorFlow Example.
_FILE_PATTERN = '%s-*'

def get_dataset(FLAGS, dataset_name, split_name, dataset_dir):
  """Gets an instance of slim Dataset.

  Args:
    dataset_name: Dataset name.
    split_name: A train/val Split name.
    dataset_dir: The directory of the dataset sources.

  Returns:
    An instance of slim Dataset.

  Raises:
    ValueError: if the dataset_name or split_name is not recognized.
  """
  if dataset_name not in _DATASETS_INFORMATION:
    raise ValueError('The specified dataset is not supported yet.')

  splits_to_sizes = _DATASETS_INFORMATION[dataset_name].splits_to_sizes

  if split_name not in splits_to_sizes:
    raise ValueError('data split name %s not recognized' % split_name)

  # Prepare the variables for different datasets.
  num_classes = _DATASETS_INFORMATION[dataset_name].num_classes
  SHAPE_DIMS = _DATASETS_INFORMATION[dataset_name].shape_dims
  SHAPE_BINS = _DATASETS_INFORMATION[dataset_name].shape_bins
  pose_range = _DATASETS_INFORMATION[dataset_name].pose_range
  bin_nums = _DATASETS_INFORMATION[dataset_name].bin_nums
  output_names = _DATASETS_INFORMATION[dataset_name].output_names
  output_names_summary = _DATASETS_INFORMATION[dataset_name].output_names_summary
  # ignore_label = _DATASETS_INFORMATION[dataset_name].ignore_label
  # height = _DATASETS_INFORMATION[dataset_name].height
  # width = _DATASETS_INFORMATION[dataset_name].width
  height_ori = _DATASETS_INFORMATION[dataset_name].height_ori
  width_ori = _DATASETS_INFORMATION[dataset_name].width_ori

  file_pattern = _FILE_PATTERN
  file_pattern = os.path.join(dataset_dir, file_pattern % split_name)

  # Specify how the TF-Examples are **decoded**
  if split_name != 'test':
      keys_to_features = {
          'image/encoded': tf.FixedLenFeature(
              (), tf.string, default_value=''),
          'image/filename': tf.FixedLenFeature(
              (), tf.string, default_value=''),
          'image/format': tf.FixedLenFeature(
              (), tf.string, default_value='png'),
          'image/height': tf.FixedLenFeature(
              (), tf.int64, default_value=0),
          'image/width': tf.FixedLenFeature(
              (), tf.int64, default_value=0),
          # 'image/posemap/class/encoded': tf.VarLenFeature(dtype=tf.float32),
          'posedict/encoded': tf.VarLenFeature(dtype=tf.float32),
          'rotuvddict/encoded': tf.VarLenFeature(dtype=tf.float32),
          'bboxdict/encoded': tf.VarLenFeature(dtype=tf.float32),
          'shapeiddict/encoded': tf.VarLenFeature(dtype=tf.float32),
          'vis/encoded': tf.FixedLenFeature(
              (), tf.string, default_value=''),
          'vis/format': tf.FixedLenFeature(
              (), tf.string, default_value='png'),
          'depth/encoded': tf.FixedLenFeature(
              (), tf.string, default_value=''),
          'depth/format': tf.FixedLenFeature(
              (), tf.string, default_value='png'),
          'seg/encoded': tf.FixedLenFeature(
              (), tf.string, default_value=''),
          'seg/format': tf.FixedLenFeature(
              (), tf.string, default_value='png'),
          'shape_id_map/encoded': tf.FixedLenFeature(
              (), tf.string, default_value=''),
          'shape_id_map/format': tf.FixedLenFeature(
              (), tf.string, default_value='png'),
      }
      items_to_handlers = {
          'image': tfexample_decoder.Image(
              image_key='image/encoded',
              format_key='image/format',
              channels=3),
          'vis': tfexample_decoder.Image(
              image_key='vis/encoded',
              format_key='vis/format',
              channels=3),
          'depth': tfexample_decoder.Image(
              image_key='depth/encoded',
              format_key='depth/format',
              channels=1,
              dtype=tf.uint16),
          'seg': tfexample_decoder.Image(
              image_key='seg/encoded',
              format_key='seg/format',
              channels=1),
          'image_name': tfexample_decoder.Tensor('image/filename'),
          'height': tfexample_decoder.Tensor('image/height'),
          'width': tfexample_decoder.Tensor('image/width'),
          # 'labels_class': tfexample_decoder.Tensor('image/posemap/class/encoded')
          'pose_dict': tfexample_decoder.Tensor('posedict/encoded'),
          'rotuvd_dict': tfexample_decoder.Tensor('rotuvddict/encoded'),
          'bbox_dict': tfexample_decoder.Tensor('bboxdict/encoded'),
          'shape_id_dict': tfexample_decoder.Tensor('shapeiddict/encoded'),
          'shape_id_map': tfexample_decoder.Image(
              image_key='shape_id_map/encoded',
              format_key='shape_id_map/format',
              channels=1),
      }
  else:
      keys_to_features = {
          'image/encoded': tf.FixedLenFeature(
              (), tf.string, default_value=''),
          'image/filename': tf.FixedLenFeature(
              (), tf.string, default_value=''),
          'image/format': tf.FixedLenFeature(
              (), tf.string, default_value='png'),
          'image/height': tf.FixedLenFeature(
              (), tf.int64, default_value=0),
          'image/width': tf.FixedLenFeature(
              (), tf.int64, default_value=0),
          'seg/encoded': tf.FixedLenFeature(
              (), tf.string, default_value=''),
          'seg/format': tf.FixedLenFeature(
              (), tf.string, default_value='png'),
      }
      items_to_handlers = {
          'image': tfexample_decoder.Image(
              image_key='image/encoded',
              format_key='image/format',
              channels=3),
          'seg': tfexample_decoder.Image(
              image_key='seg/encoded',
              format_key='seg/format',
              channels=1),
          'image_name': tfexample_decoder.Tensor('image/filename'),
          'height': tfexample_decoder.Tensor('image/height'),
          'width': tfexample_decoder.Tensor('image/width'),
      }

  decoder = tfexample_decoder.TFExampleDecoder(
      keys_to_features, items_to_handlers)
  return dataset.Dataset(
      data_sources=file_pattern,
      reader=tf.TFRecordReader,
      decoder=decoder,
      num_samples=splits_to_sizes[split_name],
      items_to_descriptions=_ITEMS_TO_DESCRIPTIONS,
      # ignore_label=ignore_label,
      pose_range=pose_range,
      bin_nums=bin_nums,
      SHAPE_DIMS=SHAPE_DIMS,
      output_names=output_names,
      output_names_summary=output_names_summary,
      num_classes=num_classes,
      # shape_dims=shape_dims,
      SHAPE_BINS=SHAPE_BINS,
      POSE_BINS=POSE_BINS,
      name=dataset_name,
      # height=height,
      # width=width,
      height_ori=height_ori,
      width_ori=width_ori,
      multi_label=True,
      if_depth=FLAGS.if_depth)

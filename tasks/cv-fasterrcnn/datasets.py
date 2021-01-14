import cv2
import numpy as np
import pandas as pd
import albumentations as A
from albumentations.pytorch.transforms import ToTensorV2

import torch
from torch.utils.data import Dataset


class DatasetManager(Dataset):


    def __init__(self, dataframe, image_dir, transforms=None, step = "Experiment"):
        super().__init__()

        self.image_ids = dataframe['image_id'].unique()
        self.df = dataframe
        self.image_dir = image_dir
        self.transforms = transforms
        self.step = step


    def __getitem__(self, index: int):

        image_id = self.image_ids[index]
        records = self.df[self.df['image_id'] == image_id]
        image = cv2.imread(f'{self.image_dir}/{image_id}.jpg', cv2.IMREAD_COLOR)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB).astype(np.float32)
        image /= 255.0


        if self.step ==  "Experiment":

            # transforming [x_min, y_min, width, height] to x_min, y_min, x_max, y_max]
            # it is an albumentations requirement
            boxes = records[['x', 'y', 'w', 'h']].values
            boxes[:, 2] = boxes[:, 0] + boxes[:, 2]
            boxes[:, 3] = boxes[:, 1] + boxes[:, 3]
            
            area = (boxes[:, 3] - boxes[:, 1]) * (boxes[:, 2] - boxes[:, 0])
            area = torch.as_tensor(area, dtype=torch.float32)

            # there is only one class
            labels = torch.ones((records.shape[0],), dtype=torch.int64)
            
            # suppose all instances are not crowd
            iscrowd = torch.zeros((records.shape[0],), dtype=torch.int64)
            
            target = {}
            target['boxes'] = boxes
            target['labels'] = labels
            # target['masks'] = None
            target['image_id'] = torch.tensor([index])
            target['area'] = area
            target['iscrowd'] = iscrowd

            if self.transforms:
                sample = {'image': image,'bboxes': target['boxes'],'labels': labels}
                sample = self.transforms(**sample)
                image = sample['image']
                
                # Reempilia as bboxes em m tensor só como estava antes
            stacked_boxes = torch.stack(tuple(map(torch.tensor, zip(*sample['bboxes'])))).permute(1, 0)
            target['boxes'] = torch.as_tensor(stacked_boxes, dtype=torch.float32)


            return image, image_id,target

        if self.step ==  "Deployment":
            
            if self.transforms:
                
                sample = {'image': image,}
                sample = self.transforms(**sample)
                image = sample['image']

            return image, image_id
   

    def __len__(self) -> int:
        return self.image_ids.shape[0]
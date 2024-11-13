import pandas as pd
import numpy as np
import torch
from sklearn.model_selection import train_test_split
from transformers import BertTokenizer, BertForSequenceClassification, Trainer, TrainingArguments
from torch.utils.data import Dataset

# Загружаем и подготавливаем данные
data = {
    'text': ['текст 1', 'текст 2', '...', 'текст с классом 1'] * 10000,
    'label': [1] * 37000 + [0] * 4000
}
df = pd.DataFrame(data)

# Разделяем данные на обучающую и тестовую выборки
X_train, X_test, y_train, y_test = train_test_split(df['text'], df['label'], test_size=0.1, random_state=42)

# Класс для создания датасета
class CustomDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = self.texts[idx]
        label = self.labels[idx]
        
        encoding = self.tokenizer.encode_plus(
            text,
            max_length=self.max_len,
            truncation=True,
            padding='max_length',
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

# Инициализация токенизатора и датасетов
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
train_dataset = CustomDataset(X_train.tolist(), y_train.tolist(), tokenizer, max_len=128)
test_dataset = CustomDataset(X_test.tolist(), y_test.tolist(), tokenizer, max_len=128)

# Настройки обучения
training_args = TrainingArguments(
    output_dir='./results',
    num_train_epochs=3,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=64,
    warmup_steps=500,
    weight_decay=0.01,
    logging_dir='./logs',
    logging_steps=10,
)

# Инициализация модели
model = BertForSequenceClassification.from_pretrained('bert-base-uncased', num_labels=2)

# Взвешивание классов
from sklearn.utils.class_weight import compute_class_weight

class_weights = compute_class_weight('balanced', classes=np.unique(y_train), y=y_train)
class_weights = torch.tensor(class_weights, dtype=torch.float)

# Обучение
class_weights = class_weights.to('cuda') if torch.cuda.is_available() else class_weights

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=test_dataset,
    compute_metrics=lambda p: {
        'accuracy': (p.predictions.argmax(-1) == p.label_ids).mean(),
    }
)

trainer.train()

# Сохраняем модель
model.save_pretrained('./my_model')
tokenizer.save_pretrained('./my_model')

# Использование модели для предсказаний
def predict(text):
    model.eval()
    inputs = tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
    predictions = torch.argmax(outputs.logits, dim=1)
    return predictions.item()

# Пример предсказания
new_text = "Тестовый текст для предсказания"
prediction = predict(new_text)
print(f"Предсказанный класс: {prediction}")


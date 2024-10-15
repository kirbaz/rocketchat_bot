from transformers import BertTokenizer, BertForSequenceClassification, DistilBertTokenizer, DistilBertForSequenceClassification
from torch.utils.data import DataLoader, Dataset
from torch.optim import Adam
import torch

# Пример пользовательского датасета
class CustomDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = self.texts[idx]
        label = self.labels[idx]
        encoding = self.tokenizer(
            text,
            add_special_tokens=True,
            max_length=self.max_length,
            return_token_type_ids=False,
            padding='max_length',
            return_attention_mask=True,
            return_tensors='pt',
        )
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

# Инициализация токенайзера и модели
tokenizer = BertTokenizer.from_pretrained('bert-base-multilingual-uncased')
model = BertForSequenceClassification.from_pretrained('bert-base-multilingual-uncased', num_labels=2)

# Для DistilBERT достаточно заменить две строки выше следующими строками:
# tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-multilingual-cased')
# model = DistilBertForSequenceClassification.from_pretrained('distilbert-base-multilingual-cased')

texts = ["пример текста 1", "пример текста 2", ...]  # Ваши тексты
labels = [0, 1, ...]  # Ваши метки

# Параметры обучения
batch_size = 16
epochs = 3
max_length = 128
learning_rate = 5e-5

# Создание DataLoader
dataset = CustomDataset(texts, labels, tokenizer, max_length)
dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

# Инициализация оптимизатора
optimizer = Adam(model.parameters(), lr=learning_rate)

# Цикл обучения
for epoch in range(epochs):
    print(f'Epoch {epoch + 1}/{epochs}')
    model.train()
    for batch in dataloader:
        input_ids = batch['input_ids']
        attention_mask = batch['attention_mask']
        labels = batch['labels']
        
        # Обнуление градиентов
        optimizer.zero_grad()
        
        # Прямой проход
        outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
        loss = outputs.loss
        
        # Обратный проход
        loss.backward()
        
        # Обновление параметров
        optimizer.step()
        
        print(f'Loss: {loss.item()}')

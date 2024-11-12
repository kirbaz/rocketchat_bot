from transformers import BertTokenizer, BertForSequenceClassification, Trainer, TrainingArguments
from datasets import load_dataset
import torch

# Загрузка BERT Tokenizer и модели
model_name = 'bert-base-uncased'
tokenizer = BertTokenizer.from_pretrained(model_name)
model = BertForSequenceClassification.from_pretrained(model_name, num_labels=2)

# Подготовка датасета
# Предположим, что у вас есть датасет с колонками 'text' и 'label'
dataset = load_dataset('csv', data_files='path/to/your/dataset.csv')

# Токенизация текста
def tokenize(batch):
    return tokenizer(batch['text'], padding=True, truncation=True)

tokenized_dataset = dataset.map(tokenize, batched=True)

# Взвешивание классов
class_weights = torch.tensor([0.1, 0.9])  # Пример весов: [вес для класса 0, вес для класса 1]
class_weights = class_weights.to('cuda' if torch.cuda.is_available() else 'cpu')

# Переопределение функции потерь
def compute_loss(outputs, labels):
    loss_fct = torch.nn.CrossEntropyLoss(weight=class_weights)
    return loss_fct(outputs.logits, labels)

# Настройки тренировки
training_args = TrainingArguments(
    output_dir='./results',
    num_train_epochs=3,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    warmup_steps=500,
    weight_decay=0.01,
    logging_dir='./logs',
    logging_steps=10,
    evaluation_strategy="epoch",
    save_strategy="epoch",
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset['train'],
    eval_dataset=tokenized_dataset['validation'],
    compute_metrics=lambda p: {"accuracy": (p.predictions.argmax(-1) == p.label_ids).mean()},
    loss_fn=compute_loss
)

# Обучение модели
trainer.train()

# Сохранение модели на диск
trainer.save_model("./trained_bert_model")

# Использование модели для предсказаний
from transformers import pipeline

# Загрузка сохраненной модели
model_path = "./trained_bert_model"
inference_model = BertForSequenceClassification.from_pretrained(model_path)
inference_tokenizer = BertTokenizer.from_pretrained(model_path)

# Создание пайплайна для предсказаний
text_classification = pipeline("text-classification", model=inference_model, tokenizer=inference_tokenizer)

# Пример предсказания
texts = ["Your new text here", "Another text for prediction"]
predictions = text_classification(texts)

print(predictions)
